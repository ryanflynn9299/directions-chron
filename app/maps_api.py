# app/maps_api.py
import logging
import requests
from typing import Optional


def get_fastest_travel_time(api_key: str, origin: str, destination: str) -> Optional[int]:
    """
    Fetches the fastest travel time between two points using the Google Maps Directions API.

    Args:
        api_key: Your Google Maps API key.
        origin: The starting point address or coordinates.
        destination: The ending point address or coordinates.

    Returns:
        The travel time in seconds, or None if the request fails.
    """
    base_url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": api_key,
        "departure_time": "now",  # Use real-time traffic
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()

        if data["status"] == "OK":
            # The API can return multiple routes, we assume the first is the best.
            route = data["routes"][0]
            leg = route["legs"][0]
            # 'duration_in_traffic' is the most accurate value when available
            if 'duration_in_traffic' in leg:
                return leg['duration_in_traffic']['value']
            else:
                return leg['duration']['value']
        else:
            logging.error(f"Google Maps API returned status: {data['status']}. Error: {data.get('error_message')}")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP request to Google Maps API failed: {e}")
        return None
    except (KeyError, IndexError) as e:
        logging.error(f"Failed to parse Google Maps API response: {e}")
        return None
