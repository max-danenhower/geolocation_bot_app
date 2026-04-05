from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Annotated
import torch
from torch import nn
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import io
import numpy as np
from database import engine, get_db
from models import Base, Prediction
from sqlalchemy.orm import Session

# create prediction table if it doesn't exist
Base.metadata.create_all(bind=engine)

# max file size for uploads (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# set device for torch
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

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
).to(device)

# load pretrained weights
regressor.load_state_dict(torch.load("model_weights.pth", map_location=device))

# load CLIP model and processor
street_clip_model = CLIPModel.from_pretrained("geolocal/StreetCLIP").to(device)
street_clip_processor = CLIPProcessor.from_pretrained("geolocal/StreetCLIP")

# load coordinate normalization stats (from training data)
lat_min, lat_max, lon_min, lon_max = np.load('coord_stats.npy')

# create FastAPI app
app = FastAPI()

def run_model(image: Image.Image):
    '''
    Run the image through the CLIP model and regressor to get predicted coordinates. Returns a dict with lat and lng.
    '''


    # embed image
    inputs = street_clip_processor(images=image, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

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

    print(f"Predicted coordinates: {norm_lat}, {norm_lon}")

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