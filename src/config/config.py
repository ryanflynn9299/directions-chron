import os
import yaml
from dotenv import load_dotenv

# Load environment variables from the .env file in the project root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Load defaults from config.yaml
yaml_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.yaml')
try:
    with open(yaml_path, 'r') as f:
        yaml_config = yaml.safe_load(f) or {}
except FileNotFoundError:
    yaml_config = {}

# --- API Configuration (Sensitive / Environment Specific) ---
_api_cfg = yaml_config.get('api', {})
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

_mock_env = os.getenv("MOCK_API_CALLS")
if _mock_env is not None:
    MOCK_API_CALLS = _mock_env.lower() in ('true', '1', 't')
else:
    MOCK_API_CALLS = _api_cfg.get('mock_api_calls', False)

# --- Default Route Configuration ---
# Values from .env override yaml defaults which override hardcoded defaults
_default_routes = yaml_config.get('default_routes', {})
START_POINT = os.getenv("START_POINT", _default_routes.get('start_point'))
END_POINT = os.getenv("END_POINT", _default_routes.get('end_point'))

if not all([API_KEY, START_POINT, END_POINT]):
    print("Warning: API_KEY, START_POINT, and END_POINT are advised to be set.")

_collect_return_env = os.getenv("COLLECT_RETURN_TRIP")
if _collect_return_env is not None:
    COLLECT_RETURN_TRIP = _collect_return_env.lower() in ('true', '1', 't')
else:
    COLLECT_RETURN_TRIP = _default_routes.get('collect_return_trip', False)

# --- Application Settings (Defaults) ---
_schedule_cfg = yaml_config.get('schedule', {})
try:
    INTERVAL_MINUTES = int(os.getenv("COLLECTION_INTERVAL_MINUTES", _schedule_cfg.get('peak_interval_minutes', 5)))
    STUDY_DURATION_DAYS = int(os.getenv("STUDY_DURATION_DAYS", _schedule_cfg.get('study_duration_days', 14)))
    
    OFF_PEAK_INTERVAL_MINUTES = int(_schedule_cfg.get('off_peak_interval_minutes', 30))
    OFF_PEAK_START_TIME = _schedule_cfg.get('off_peak_start_time', "21:00")
    OFF_PEAK_END_TIME = _schedule_cfg.get('off_peak_end_time', "04:00")
except (ValueError, TypeError):
    print("Invalid numerical value for interval or duration. Using fallback defaults.")
    INTERVAL_MINUTES = 5
    STUDY_DURATION_DAYS = 14
    OFF_PEAK_INTERVAL_MINUTES = 30
    OFF_PEAK_START_TIME = "21:00"
    OFF_PEAK_END_TIME = "04:00"

# --- Database Configuration ---
DB_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'traffic_data.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Path for the file that stores the study's end time to persist state
STUDY_STATE_FILE = os.path.join(DB_DIR, 'study_state.json')
