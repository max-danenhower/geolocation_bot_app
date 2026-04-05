from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from typing import Optional, Annotated
import torch
from torch import nn
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import io
import numpy as np

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

regressor.load_state_dict(torch.load("model_weights.pth", map_location=device))

# load CLIP model and processor
street_clip_model = CLIPModel.from_pretrained("geolocal/StreetCLIP").to(device)
street_clip_processor = CLIPProcessor.from_pretrained("geolocal/StreetCLIP")

app = FastAPI()

def run_model(file: Image.Image):

    def embed_image(byte_encoding):
        '''
        Generate an image embedding using StreetCLIP. Uses the images byte encoding

        args: the image byte encoding
        returns: a tensor of the image embedding
        '''
        # Load image
        image = Image.open(io.BytesIO(byte_encoding)).convert('RGB')

        # Process image
        inputs = street_clip_processor(images=image, return_tensors="pt", padding=True)
        for k in inputs:
            inputs[k] = inputs[k].to(device)

        with torch.no_grad():
            image_feat = street_clip_model.get_image_features(**inputs)
            image_feat = image_feat / image_feat.norm(dim=-1, keepdim=True)

        return image_feat.squeeze(0)
    
    # read image from uploaded file
    image_bytes = file.file.read()
    
    # embed image using StreetCLIP
    image_embedding = embed_image(image_bytes)
    
    # predict coordinates using MLP
    regressor.eval()
    pred_lat,pred_lon = regressor(image_embedding)

    # load coordinate normalization stats (from training data)
    lat_min, lat_max, lon_min, lon_max = np.load('coord_stats.npy')

    def denormalize_coords(lat_norm,lon_norm):
        norm_lat = lat_norm * (lat_max - lat_min) + lat_min
        norm_lon = lon_norm * (lon_max - lon_min) + lon_min
        return norm_lat,norm_lon

    norm_lat, norm_lon = denormalize_coords(pred_lat,pred_lon)

    print(f"Predicted coordinates: {norm_lat}, {norm_lon}")

    return {"lat": float(norm_lat), "lng": float(norm_lon)}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    return run_model(file)