from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Annotated
import torch
from torch import nn
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import io
import dask.dataframe as dd
import random
import base64
from io import BytesIO
import numpy as np
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from math import radians, sin, cos, sqrt, atan2

from database import engine, get_db
from models import Base, Prediction, Round

# create prediction table if it doesn't exist
Base.metadata.create_all(bind=engine)

# max file size for uploads (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# define MLP
regressor = nn.Sequential(
    nn.Linear(768, 512),
    nn.ReLU(),
    nn.Linear(512, 256),
    nn.ReLU(),
    nn.Linear(256, 128),
    nn.ReLU(),
    nn.Linear(128, 2),
    nn.Sigmoid()
)

# load pretrained weights
regressor.load_state_dict(torch.load("model_weights.pth"))

# load CLIP model and processor
street_clip_model = CLIPModel.from_pretrained("geolocal/StreetCLIP")
street_clip_processor = CLIPProcessor.from_pretrained("geolocal/StreetCLIP")

# load coordinate normalization stats (from training data)
lat_min, lat_max, lon_min, lon_max = np.load('coord_stats.npy')

# load dataset once at startup
dataset = dd.read_parquet("hf://datasets/stochastic/random_streetview_images_pano_v0.0.2/data/train-*-of-*.parquet")
image_pool = dataset.head(100) # load 100 samples into memory for quick access

# store active rounds in memory (for simplicity, not using DB for this)
active_rounds = {}  # round_id -> {true_lat, true_lng, ai_lat, ai_lng}

# create FastAPI app
app = FastAPI()

# allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_model(image: Image.Image):
    '''
    Run the image through the CLIP model and regressor to get predicted coordinates. Returns a dict with lat and lng.
    '''


    # embed image
    inputs = street_clip_processor(images=image, return_tensors="pt", padding=True)

    with torch.no_grad():
        image_feat = street_clip_model.get_image_features(**inputs)
        image_feat = image_feat / image_feat.norm(dim=-1, keepdim=True)

    # predict coords
    with torch.no_grad():
        pred = regressor(image_feat)

    pred_lat, pred_lon = pred[0][0], pred[0][1]

    def denormalize_coords(lat_norm,lon_norm):
        norm_lat = lat_norm * (lat_max - lat_min) + lat_min
        norm_lon = lon_norm * (lon_max - lon_min) + lon_min
        return norm_lat,norm_lon

    norm_lat, norm_lon = denormalize_coords(pred_lat,pred_lon)

    return {"lat": float(norm_lat), "lng": float(norm_lon)}

@app.post("/predict")
async def predict(file: UploadFile = File(...), db: Session = Depends(get_db)):
    '''
    Endpoint to receive an image file, run it through the model, and return predicted coordinates. 
    Validates file type and size, and checks that the image can be read.
    '''

    # check file type
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG, or WEBP image")

    contents = await file.read()

    # check file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size must be under 10MB")

    # check image is readable
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read image file")
    
    try:
        result = run_model(image)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in run_model: {str(e)}")

    try:
        # save to db
        prediction = Prediction(
            predicted_lat=result["lat"],
            predicted_lng=result["lng"]
        )
        db.add(prediction)
        db.commit()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving to database: {str(e)}")
    
@app.get("/round")
def get_round(db: Session = Depends(get_db)):
    # pick random row
    idx = random.randint(0, len(image_pool) - 1)
    row = image_pool.iloc[idx]

    # get image bytes and encode as base64 for sending to frontend
    img_bytes = row["image"]["bytes"]
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    # run AI prediction
    image = Image.open(BytesIO(img_bytes)).convert("RGB")
    ai_result = run_model(image)

    # store round in db
    round_entry = Round(
        true_lat=row["latitude"],
        true_lng=row["longitude"],
        ai_lat=ai_result["lat"],
        ai_lng=ai_result["lng"]
    )
    db.add(round_entry)
    db.commit()
    db.refresh(round_entry)

    # cache in memory so /score can look it up
    active_rounds[round_entry.id] = {
        "true_lat": row["latitude"],
        "true_lng": row["longitude"],
        "ai_lat": ai_result["lat"],
        "ai_lng": ai_result["lng"]
    }

    print('after round', active_rounds)

    return {
        "round_id": round_entry.id,
        "image": img_base64
    }

class ScoreRequest(BaseModel):
    round_id: int
    user_lat: float
    user_lng: float

def haversine(lat1, lng1, lat2, lng2):
    '''
    Distance in miles between two lat/lng points using Haversine formula
    '''
    R = 3958.8  # Earth radius in miles
    print(lat1, lng1, lat2, lng2)
    lat1, lng1, lat2, lng2 = map(radians, [float(lat1), float(lng1), float(lat2), float(lng2)])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

@app.post("/score")
def get_score(request: ScoreRequest, db: Session = Depends(get_db)):
    round_data = active_rounds.get(request.round_id)
    print('in score', active_rounds)
    print('round data', round_data)
    if not round_data:
        raise HTTPException(status_code=404, detail="Round not found")

    user_distance = haversine(request.user_lat, request.user_lng, round_data["true_lat"], round_data["true_lng"])
    ai_distance = haversine(round_data["ai_lat"], round_data["ai_lng"], round_data["true_lat"], round_data["true_lng"])

    # update db with user guess
    round_entry = db.query(Round).filter(Round.id == request.round_id).first()
    round_entry.user_lat = request.user_lat
    round_entry.user_lng = request.user_lng
    round_entry.user_distance_km = user_distance
    round_entry.ai_distance_km = ai_distance
    db.commit()

    # clean up memory
    del active_rounds[request.round_id]

    return {
        "true_lat": round_data["true_lat"],
        "true_lng": round_data["true_lng"],
        "ai_lat": round_data["ai_lat"],
        "ai_lng": round_data["ai_lng"],
        "user_distance_km": round(user_distance, 2),
        "ai_distance_km": round(ai_distance, 2),
        "user_won": user_distance < ai_distance
    }