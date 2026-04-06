from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    predicted_lat = Column(Float, nullable=False)
    predicted_lng = Column(Float, nullable=False)
    image_path = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(Integer, nullable=True)  # null for now, populated when you add auth

class Round(Base):
    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True, index=True)
    true_lat = Column(Float, nullable=False)
    true_lng = Column(Float, nullable=False)
    ai_lat = Column(Float, nullable=False)
    ai_lng = Column(Float, nullable=False)
    user_lat = Column(Float, nullable=True)
    user_lng = Column(Float, nullable=True)
    user_distance_km = Column(Float, nullable=True)
    ai_distance_km = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)