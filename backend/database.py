import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path="../.env", override=False)
print(f"Current Environment Keys: {os.environ.keys()}")

print("DATABASE_URL:", os.getenv("DATABASE_URL"))


def get_engine(retries=5, delay=3):
    for i in range(retries):
        try:
            engine = create_engine(os.getenv("DATABASE_URL"))
            engine.connect()
            print("Database connected")
            return engine
        except Exception as e:
            print(f"Database not ready, retrying in {delay}s... ({i+1}/{retries})")
            time.sleep(delay)
    raise Exception("Could not connect to database after retries")

engine = get_engine()
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()