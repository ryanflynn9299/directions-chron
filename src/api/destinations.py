from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import json

from src.db.database import get_db_session
from src.db.models import DestinationBatch
from src.api.schemas import DestinationBatchCreate, DestinationBatchResponse

router = APIRouter(prefix="/destinations", tags=["destinations"])

@router.post("/batch", response_model=DestinationBatchResponse)
async def create_or_update_batch(batch: DestinationBatchCreate):
    """Creates or updates a destination batch alias."""
    destinations_json = json.dumps(batch.destinations)
    
    with get_db_session() as db:
        try:
            # Check if exists
            existing_batch = db.query(DestinationBatch).filter(DestinationBatch.alias == batch.alias).first()
            
            if existing_batch:
                existing_batch.destinations_json = destinations_json
            else:
                new_batch = DestinationBatch(alias=batch.alias, destinations_json=destinations_json)
                db.add(new_batch)
                
            db.commit()
            return batch
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to save destination batch: {e}")

@router.get("/batch/{alias}", response_model=DestinationBatchResponse)
async def get_batch(alias: str):
    """Retrieves a specific destination batch by alias."""
    with get_db_session() as db:
        batch = db.query(DestinationBatch).filter(DestinationBatch.alias == alias).first()
        if not batch:
            raise HTTPException(status_code=404, detail=f"Destination batch '{alias}' not found")
            
        return DestinationBatchResponse(
            alias=batch.alias,
            destinations=json.loads(batch.destinations_json)
        )

@router.get("/batch", response_model=List[DestinationBatchResponse])
async def list_batches():
    """Lists all stored destination batches."""
    with get_db_session() as db:
        batches = db.query(DestinationBatch).all()
        
        return [
            DestinationBatchResponse(
                alias=b.alias,
                destinations=json.loads(b.destinations_json)
            ) for b in batches
        ]

@router.delete("/batch/{alias}")
async def delete_batch(alias: str):
    """Deletes a destination batch by alias."""
    with get_db_session() as db:
        batch = db.query(DestinationBatch).filter(DestinationBatch.alias == alias).first()
        if not batch:
            raise HTTPException(status_code=404, detail=f"Destination batch '{alias}' not found")
            
        try:
            db.delete(batch)
            db.commit()
            return {"status": "success", "message": f"Deleted destination batch '{alias}'"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to delete batch: {e}")
