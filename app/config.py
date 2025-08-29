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

# NEW: Parse the boolean flag for collecting the return trip
COLLECT_RETURN_TRIP = os.getenv("COLLECT_RETURN_TRIP", "false").lower() in ('true', '1', 't')

# --- Application Settings ---
try:
    # Interval in minutes for data collection
    INTERVAL_MINUTES = int(os.getenv("COLLECTION_INTERVAL_MINUTES", 5))
    # Total duration in days for the study
    STUDY_DURATION_DAYS = int(os.getenv("STUDY_DURATION_DAYS", 14))

    # Interval in minutes for data collection off-peak
    OFF_PEAK_INTERVAL_MINUTES = 30
    # Hour to start off-peak scheduling (9 PM)
    OFF_PEAK_START_HOUR = 21
    # Hour to end off-peak scheduling (4 AM)
    OFF_PEAK_END_HOUR = 4
except (ValueError, TypeError):
    print("Invalid numerical value for interval or duration. Using defaults.")
    INTERVAL_MINUTES = 5
    STUDY_DURATION_DAYS = 14
    OFF_PEAK_INTERVAL_MINUTES = 30
    OFF_PEAK_START_HOUR = 21
    OFF_PEAK_END_HOUR = 4

# --- Database Configuration ---
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'traffic_data.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Path for the file that stores the study's end time to persist state
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
STUDY_STATE_FILE = os.path.join(DATA_DIR, 'study_state.json')
