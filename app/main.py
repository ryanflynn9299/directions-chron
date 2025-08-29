# app/main.py
import logging
import schedule
import sys
import time
import json
from datetime import datetime, timedelta

import config
import database
import maps_api
from app import maps_api2

# Configure logging for clear and informative output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# --- CONSTANTS for schedule tags ---
PEAK_JOB_TAG = 'peak-job'
OFF_PEAK_JOB_TAG = 'off-peak-job'


def collect_traffic_data_job():
    """The main job function to be scheduled. It fetches and stores traffic data."""

    # --- Collect Primary Route (A -> B) ---
    logging.info(f"Fetching primary route: '{config.START_POINT}' -> '{config.END_POINT}'.")
    duration_seconds_ab = maps_api2.get_route_duration_seconds(
        api_key=config.API_KEY,
        origin=config.START_POINT,
        destination=config.END_POINT
    )
    if duration_seconds_ab is not None:
        database.add_traffic_entry(
            duration_seconds=duration_seconds_ab,
            origin=config.START_POINT,
            destination=config.END_POINT
        )
    else:
        logging.warning("Could not retrieve travel time for the primary route.")

    # --- Collect Return Route (B -> A) if configured ---
    if config.COLLECT_RETURN_TRIP:
        # Small sleep to avoid hitting API rate limits if any
        time.sleep(2)

        logging.info(f"Fetching return route: '{config.END_POINT}' -> '{config.START_POINT}'.")
        duration_seconds_ba = maps_api2.get_route_duration_seconds(
            api_key=config.API_KEY,
            origin=config.END_POINT,
            destination=config.START_POINT
        )
        if duration_seconds_ba is not None:
            database.add_traffic_entry(
                duration_seconds=duration_seconds_ba,
                origin=config.END_POINT,
                destination=config.START_POINT
            )
        else:
            logging.warning("Could not retrieve travel time for the return route.")


def is_off_peak_hours() -> bool:
    """Checks if the current time is within the defined off-peak hours."""
    current_hour = datetime.now().hour
    start = config.OFF_PEAK_START_HOUR
    end = config.OFF_PEAK_END_HOUR
    # This handles the overnight case (e.g., 9 PM to 4 AM)
    if start > end:
        return current_hour >= start or current_hour < end
    else:
        return start <= current_hour < end


def manage_schedule():
    """
    The core scheduler. Checks the time and ensures the correct jobs
    (peak or off-peak) are scheduled at predictable, clock-aligned times.
    """
    # Clear any previously tagged jobs to prevent duplicates
    schedule.clear(PEAK_JOB_TAG)
    schedule.clear(OFF_PEAK_JOB_TAG)

    if is_off_peak_hours():
        # --- Schedule Off-Peak Jobs ---
        # Only set the schedule if it isn't already set for this mode
        if not schedule.get_jobs(OFF_PEAK_JOB_TAG):
            logging.info(f"Off-peak hours. Scheduling to run at :00 and :30 past the hour.")
            schedule.every().hour.at(":00").do(collect_traffic_data_job).tag(OFF_PEAK_JOB_TAG)
            schedule.every().hour.at(":30").do(collect_traffic_data_job).tag(OFF_PEAK_JOB_TAG)
    else:
        # --- Schedule Peak Jobs ---
        # Only set the schedule if it isn't already set for this mode
        if not schedule.get_jobs(PEAK_JOB_TAG):
            logging.info(f"Peak hours. Scheduling to run every {config.INTERVAL_MINUTES} minutes.")
            for minute in range(0, 60, config.INTERVAL_MINUTES):
                # Formats the minute mark as ":00", ":05", ":10", etc.
                schedule.every().hour.at(f":{minute:02d}").do(collect_traffic_data_job).tag(PEAK_JOB_TAG)


def get_study_end_time() -> datetime:
    """
    Loads the study end time from the state file. If the file doesn't exist,
    it calculates a new end time, saves it, and returns it.
    """
    try:
        with open(config.STUDY_STATE_FILE, 'r') as f:
            state_data = json.load(f)
            end_time = datetime.fromisoformat(state_data['end_time'])
            logging.info(f"Loaded existing study end time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return end_time
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        logging.info("No valid state file found. Calculating new study end time.")
        start_time = datetime.now()
        end_time = start_time + timedelta(days=config.STUDY_DURATION_DAYS)

        state_data = {'end_time': end_time.isoformat()}
        with open(config.STUDY_STATE_FILE, 'w') as f:
            json.dump(state_data, f)

        logging.info(
            f"New study duration set. It will run for {config.STUDY_DURATION_DAYS} days, ending on {end_time.strftime('%Y-%m-%d %H:%M:%S')}.")
        return end_time


def main():
    """Main function to initialize and run the traffic monitor."""
    logging.info("--- Starting Traffic Data Monitor ---")

    database.init_db()
    end_time = get_study_end_time()

    if config.COLLECT_RETURN_TRIP:
        logging.info("Bidirectional data collection is ENABLED.")

    # Schedule the manager function to run every minute to adapt to time changes.
    schedule.every(1).minutes.do(manage_schedule)

    # Run the manager immediately on startup to set the correct initial schedule.
    logging.info("Setting initial collection schedule...")
    manage_schedule()

    logging.info("Scheduler is running. Main loop started.")
    while datetime.now() < end_time:
        schedule.run_pending()
        time.sleep(1)

    logging.info("--- Study duration has ended. The container will now idle. ---")
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
