import os
import sys
import random
import requests
from datetime import datetime, timedelta

# Add the project root to the python path so we can import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.database import get_db_session
from src.db.models import TrafficData

BASE_URL = "http://localhost:8000"

def seed_api_aliases():
    """Hits the live API to register a couple of routing aliases."""
    print(f"Connecting to {BASE_URL} to seed aliases...")
    
    aliases = [
        {
            "alias": "morning_commute",
            "source": "123 Suburb Ln, Town, State",
            "destination": "456 Downtown Ave, City, State",
            "bidirectional": False
        },
        {
            "alias": "evening_commute",
            "source": "456 Downtown Ave, City, State",
            "destination": "123 Suburb Ln, Town, State",
            "bidirectional": False
        }
    ]
    
    for payload in aliases:
        try:
            resp = requests.post(f"{BASE_URL}/aliases", json=payload)
            resp.raise_for_status()
            print(f" -> Successfully created alias via API: {payload['alias']}")
        except requests.exceptions.ConnectionError:
            print(" -> FATAL: Could not connect to the API. Is the FastAPI server running on port 8000?")
            sys.exit(1)
        except Exception as e:
            print(f" -> Failed to create alias {payload['alias']}. Error: {e}")
            sys.exit(1)

def seed_db_traffic_data():
    """Injects historical dummy traffic data directly into the DB for testing reporting queries."""
    print("Seeding dummy traffic data directly into the database...")
    
    with get_db_session() as session:
        # Generate 14 days of data for morning and evening commutes
        now = datetime.now()
        start_date = now - timedelta(days=14)
        
        records_to_insert = []
        
        for day in range(14):
            current_date = start_date + timedelta(days=day)
            
            # Skip weekends for more realistic business data
            if current_date.weekday() >= 5:
                continue
                
            day_str = current_date.strftime('%A')
            
            # Morning commute around 8:00 AM
            morn_time = current_date.replace(hour=8, minute=random.randint(0, 59))
            morn_origin = "123 Suburb Ln, Town, State"
            morn_dest = "456 Downtown Ave, City, State"
            morn_group = "|".join(sorted([morn_origin, morn_dest]))
            
            # Base duration around 45 mins (2700s), variance +/- 10 mins
            morn_duration = 2700 + random.randint(-600, 600)
            
            records_to_insert.append(TrafficData(
                timestamp=morn_time,
                day_of_week=day_str,
                duration_seconds=morn_duration,
                origin=morn_origin,
                destination=morn_dest,
                route_group_id=morn_group,
                job_id="seed-job-123",
                alias="morning_commute"
            ))
            
            # Evening commute around 5:00 PM
            eve_time = current_date.replace(hour=17, minute=random.randint(0, 59))
            eve_origin = "456 Downtown Ave, City, State"
            eve_dest = "123 Suburb Ln, Town, State"
            eve_group = "|".join(sorted([eve_origin, eve_dest]))
            
            # Evening traffic is typically slightly worse
            eve_duration = 2900 + random.randint(-600, 800)
            
            records_to_insert.append(TrafficData(
                timestamp=eve_time,
                day_of_week=day_str,
                duration_seconds=eve_duration,
                origin=eve_origin,
                destination=eve_dest,
                route_group_id=eve_group,
                job_id="seed-job-123",
                alias="evening_commute"
            ))
            
        session.bulk_save_objects(records_to_insert)
        session.commit()
        print(f" -> Successfully inserted {len(records_to_insert)} records of fake historical traffic data!")

if __name__ == "__main__":
    print("=== Commute Logger Data Seeder ===")
    seed_api_aliases()
    seed_db_traffic_data()
    print("=== Seeding Complete ===")
