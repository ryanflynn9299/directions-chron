# app/maps_api.py
import logging
from datetime import datetime

import requests
from typing import Optional


def get_route_duration_seconds(api_key: str, origin: str, destination: str) -> Optional[int]:
    """
    Fetches the route duration using the modern Google Routes API (computeRoutes).

    Args:
        api_key: Your Google Maps API key.
        origin: The starting point address or coordinates.
        destination: The ending point address or coordinates.

    Returns:
        The travel time in seconds, or None if the request fails.
    """
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        # FieldMask specifies which fields to return, saving data and cost.
        "X-Goog-FieldMask": "routes.duration"
    }

    body = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
    }

    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()

        if 'routes' in data and data['routes']:
            # Duration is returned as a string with 's' suffix, e.g., "3421s"
            duration_str = data['routes'][0].get('duration', '0s')
            return int(duration_str.rstrip('s'))
        else:
            # The API can return a 200 OK with an empty response if no route is found
            logging.warning(f"No routes found between {origin} and {destination}.")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP request to Google Routes API failed: {e}")
        return None
    except (KeyError, IndexError, TypeError) as e:
        logging.error(f"Failed to parse Google Routes API response: {e}")
        return None