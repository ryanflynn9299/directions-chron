from fastapi import APIRouter, HTTPException
from src.api.schemas import QueryPayload, SchedulePayload

router = APIRouter()

@router.get("/health")
async def health_check():
    """Simple API status endpoint."""
    return {"status": "healthy"}

@router.post("/routes/query")
async def execute_query(payload: QueryPayload):
    """
    Executes route fetches synchronously and returns the route data.
    """
    from src.services.route_service import RouteService
    routes_to_process = payload.routes
    
    # Execute through the bulk service handler
    results = RouteService.execute_routes_bulk(routes_to_process)
    
    return {
        "status": "success",
        "results": results
    }

@router.post("/routes/schedule")
async def create_schedule(payload: SchedulePayload):
    """
    Schedules background jobs for the provided routes based on the config.
    """
    from src.jobs.scheduler import scheduler
    
    routes = payload.routes
    config = payload.schedule

    try:
        job_id = scheduler.add_job(routes, config)
    except ValueError as e:
        # e.g., Max active jobs limit reached
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "success",
        "message": "Scheduled route queries successfully.",
        "job_id": job_id
    }

@router.get("/routes/schedule")
async def list_schedules():
    """
    Retrieves the list of all currently active background jobs.
    """
    from src.jobs.scheduler import scheduler
    return scheduler.get_jobs()
