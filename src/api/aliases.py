from fastapi import APIRouter, HTTPException
from typing import List
import json

from src.api.schemas import RouteRequest, SavedRouteResponse
from src.db.database import get_db_session
from src.db.models import SavedRoute

router = APIRouter()

@router.post("/aliases", response_model=SavedRouteResponse)
async def create_or_update_alias(request: RouteRequest):
    """
    Creates or updates a saved route alias.
    """
    # A valid full request must be provided
    if not request.alias or not request.source:
        raise HTTPException(status_code=400, detail="alias and source are unconditionally required to save an alias.")
    
    if not request.destination and not request.destinations:
        raise HTTPException(status_code=400, detail="At least one destination is required.")
        
    destinations_list = request.destinations if request.destinations else [request.destination]

    with get_db_session() as session:
        # Check for existing
        saved_route = session.query(SavedRoute).filter(SavedRoute.alias == request.alias).first()
        
        if saved_route:
            # Update
            saved_route.source = request.source
            saved_route.destinations_json = json.dumps(destinations_list)
            saved_route.bidirectional = 1 if request.bidirectional else 0
        else:
            # Create
            saved_route = SavedRoute(
                alias=request.alias,
                source=request.source,
                destinations_json=json.dumps(destinations_list),
                bidirectional=1 if request.bidirectional else 0
            )
            session.add(saved_route)
            
        session.commit()
    
    return SavedRouteResponse(
        alias=request.alias,
        source=request.source,
        destinations=destinations_list,
        bidirectional=request.bidirectional
    )

@router.get("/aliases", response_model=List[SavedRouteResponse])
async def list_aliases():
    """
    Returns all saved route aliases.
    """
    results = []
    with get_db_session() as session:
        routes = session.query(SavedRoute).all()
        for r in routes:
            results.append(SavedRouteResponse(
                alias=r.alias,
                source=r.source,
                destinations=json.loads(r.destinations_json),
                bidirectional=bool(r.bidirectional)
            ))
    return results

@router.get("/aliases/{alias_name}", response_model=SavedRouteResponse)
async def get_alias(alias_name: str):
    """
    Returns a specific saved alias.
    """
    with get_db_session() as session:
        r = session.query(SavedRoute).filter(SavedRoute.alias == alias_name).first()
        if not r:
            raise HTTPException(status_code=404, detail="Alias not found.")
            
        return SavedRouteResponse(
            alias=r.alias,
            source=r.source,
            destinations=json.loads(r.destinations_json),
            bidirectional=bool(r.bidirectional)
        )

@router.delete("/aliases/{alias_name}")
async def delete_alias(alias_name: str):
    """
    Deletes a specific saved alias.
    """
    with get_db_session() as session:
        r = session.query(SavedRoute).filter(SavedRoute.alias == alias_name).first()
        if not r:
            raise HTTPException(status_code=404, detail="Alias not found.")
            
        session.delete(r)
        session.commit()
        
    return {"status": "success", "message": f"Alias '{alias_name}' deleted successfully."}
