# app/config.py
import os
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- API and Study Configuration ---
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
START_POINT = os.getenv("START_POINT")
END_POINT = os.getenv("END_POINT")

if not all([API_KEY, START_POINT, END_POINT]):
    raise ValueError("API_KEY, START_POINT, and END_POINT must be set in the .env file.")

# --- Application Settings ---
try:
    # Interval in minutes for data collection
    INTERVAL_MINUTES = int(os.getenv("COLLECTION_INTERVAL_MINUTES", 5))
    # Total duration in days for the study
    STUDY_DURATION_DAYS = int(os.getenv("STUDY_DURATION_DAYS", 14))
except (ValueError, TypeError):
    print("Invalid numerical value for interval or duration. Using defaults.")
    INTERVAL_MINUTES = 5
    STUDY_DURATION_DAYS = 14

# --- Database Configuration ---
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'traffic_data.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"
