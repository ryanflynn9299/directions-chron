import logging
from datetime import datetime
from typing import List, Dict, Any

from src.services.maps_client import get_route_duration_seconds
from src.db.database import get_db_session
from src.db.models import TrafficData
from src.config.config import API_KEY
from src.api.schemas import RouteRequest

logger = logging.getLogger(__name__)

class RouteService:
    """Orchestrates interactions between the maps client and the database."""

    @staticmethod
    def execute_single_route(origin: str, destination: str, bidirectional: bool = True, job_id: str = None, alias: str = None) -> List[Dict[str, Any]]:
        """
        Fetches the travel time for a single origin/destination pair.
        If bidirectional is True, it also executes the reverse query.
        Persists successful retrievals to the DB.
        
        Returns:
            List of result dictionaries.
        """
        results = []
        
        # Forward trip
        res_fwd = RouteService._fetch_and_persist(origin, destination, job_id, alias)
        results.append(res_fwd)

        # Reverse trip
        if bidirectional:
            res_rev = RouteService._fetch_and_persist(destination, origin, job_id, alias)
            results.append(res_rev)

        return results

    @staticmethod
    def _fetch_and_persist(origin: str, destination: str, job_id: str = None, alias: str = None) -> Dict[str, Any]:
        """Internal helper to execute a single direction, handle errors, and persist."""
        logger.info(f"Fetching route: '{origin}' -> '{destination}'.")
        result = {
            "source": origin,
            "destination": destination,
            "duration_seconds": None,
            "status": "error",
            "error_message": None
        }

        try:
            # Future expansion point: Check Cache here

            duration_seconds = get_route_duration_seconds(
                api_key=API_KEY,
                origin=origin,
                destination=destination
            )

            if duration_seconds is not None:
                result["duration_seconds"] = duration_seconds
                result["status"] = "success"
                
                # Persist to DB
                session = get_db_session()
                try:
                    now = datetime.utcnow()
                    route_group_id = "|".join(sorted([origin, destination]))

                    new_entry = TrafficData(
                        timestamp=now,
                        day_of_week=now.strftime('%A'),
                        duration_seconds=duration_seconds,
                        origin=origin,
                        destination=destination,
                        route_group_id=route_group_id,
                        job_id=job_id,
                        alias=alias
                    )
                    session.add(new_entry)
                    session.commit()
                    logger.debug(f"Persisted entry: {origin} -> {destination}")
                except Exception as e:
                    logger.error(f"Failed to add database entry: {e}")
                    session.rollback()
                    # Still consider the API fetch a success even if persistence fails,
                    # but note the error if desired.
                finally:
                    session.close()
            else:
                result["error_message"] = "No route found or API failed"
                logger.warning(f"Could not retrieve travel time for route {origin} -> {destination}.")

        except Exception as e:
            logger.error(f"Unexpected error processing route {origin} -> {destination}: {e}")
            result["error_message"] = str(e)

        return result

    @staticmethod
    def execute_routes_bulk(routes: List[RouteRequest], job_id: str = None) -> List[Dict[str, Any]]:
        """
        Processes a list of RouteRequest objects. Evaluates 1:N destination maps.
        
        Returns:
            A flattened list of all executed result dictionaries.
        """
        all_results = []

        for route in routes:
            dests = route.destinations if route.destinations else [route.destination]
            for dest in dests:
                if dest:
                    pair_results = RouteService.execute_single_route(
                        origin=route.source,
                        destination=dest,
                        bidirectional=route.bidirectional,
                        job_id=job_id,
                        alias=route.alias
                    )
                    all_results.extend(pair_results)
                    
        return all_results
