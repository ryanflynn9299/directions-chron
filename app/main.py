# app/main.py
import logging
import schedule
import sys
import time
from datetime import datetime, timedelta

import config
import database
import maps_api

# Configure logging for clear and informative output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)


def collect_traffic_data_job():
    """
    The main job function to be scheduled. It fetches and stores traffic data.
    """
    logging.info(f"Running job: Fetching traffic data for route '{config.START_POINT}' to '{config.END_POINT}'.")

    duration_seconds = maps_api.get_fastest_travel_time(
        api_key=config.API_KEY,
        origin=config.START_POINT,
        destination=config.END_POINT
    )

    if duration_seconds is not None:
        database.add_traffic_entry(duration_seconds=duration_seconds)
        duration_minutes = duration_seconds / 60
        logging.info(f"Current fastest travel time: {duration_minutes:.2f} minutes.")
    else:
        logging.warning("Could not retrieve travel time in this interval.")


def main():
    """
    Main function to initialize and run the traffic monitor.
    """
    logging.info("--- Starting Traffic Data Monitor ---")

    # 1. Initialize the database
    database.init_db()

    # 2. Schedule the recurring job
    logging.info(f"Scheduling data collection every {config.INTERVAL_MINUTES} minutes.")
    schedule.every(config.INTERVAL_MINUTES).minutes.do(collect_traffic_data_job)

    # 3. Run the collection for the specified duration
    start_time = datetime.now()
    end_time = start_time + timedelta(days=config.STUDY_DURATION_DAYS)
    logging.info(
        f"Study will run for {config.STUDY_DURATION_DAYS} days, ending on {end_time.strftime('%Y-%m-%d %H:%M:%S')}.")

    # Run the first job immediately without waiting for the first interval
    collect_traffic_data_job()

    while datetime.now() < end_time:
        schedule.run_pending()
        time.sleep(1)  # Sleep for a second to prevent high CPU usage

    logging.info("--- Study duration has ended. Shutting down. ---")


if __name__ == "__main__":
    main()
