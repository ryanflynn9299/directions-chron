import json
from typing import List, Union

from src.api.schemas import RouteRequest
from src.db.database import get_db_session
from src.db.models import SavedRoute

def resolve_aliases(routes: List[RouteRequest]) -> List[Union[RouteRequest, dict]]:
    """
    Parses a list of RouteRequest objects. If an object is an alias-only reference,
    it attempts to look it up in the database. Returns a matched list of
    resolved RouteRequest objects and/or error dicts for missing aliases.
    """
    resolved_routes = []
    
    with get_db_session() as session:
        for r in routes:
            has_source = bool(r.source)
            has_dest = bool(r.destination)
            has_dests = bool(r.destinations)

            if r.alias and not has_source and not has_dest and not has_dests:
                # It's an alias-only resolution
                saved = session.query(SavedRoute).filter(SavedRoute.alias == r.alias).first()
                if saved:
                    resolved = RouteRequest(
                        alias=saved.alias,
                        source=saved.source,
                        destinations=json.loads(saved.destinations_json), # Schemas handles destination/destinations natively
                        bidirectional=bool(saved.bidirectional)
                    )
                    resolved_routes.append(resolved)
                else:
                    resolved_routes.append({
                        "alias": r.alias,
                        "status": "error",
                        "error_message": "Saved route alias not found"
                    })
            elif r.alias and has_source and (has_dest or has_dests):
                # An explicit route is provided with an alias label
                # Idempotently create or update the alias in the database
                dests = r.destinations if has_dests else [r.destination]
                dests_json = json.dumps(dests)
                bidi = 1 if r.bidirectional else 0
                
                saved = session.query(SavedRoute).filter(SavedRoute.alias == r.alias).first()
                if not saved:
                    new_saved = SavedRoute(
                        alias=r.alias, source=r.source, destinations_json=dests_json, bidirectional=bidi
                    )
                    session.add(new_saved)
                    resolved_routes.append({
                        "alias": r.alias,
                        "status": "alias_created",
                        "message": "Route implicitly saved as an alias."
                    })
                elif saved.source != r.source or saved.destinations_json != dests_json or saved.bidirectional != bidi:
                    saved.source = r.source
                    saved.destinations_json = dests_json
                    saved.bidirectional = bidi
                    resolved_routes.append({
                        "alias": r.alias,
                        "status": "alias_updated",
                        "message": "Existing saved alias implicitly updated."
                    })
                session.commit()
                # Ensure the explicit route itself is processed
                resolved_routes.append(r)
            else:
                # It's a standard explicit route without an alias, or lacking elements
                resolved_routes.append(r)
                
    return resolved_routes
