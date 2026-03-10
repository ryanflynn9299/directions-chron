import logging
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

from src.api.routes import router as routes_router
from src.api.aliases import router as aliases_router
from src.jobs.scheduler import scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    stream=sys.stdout
)

from src.config.config import MOCK_API_CALLS

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background scheduler task
    logger.info("--- Starting Traffic Data Monitor Application ---")
    if MOCK_API_CALLS:
        logger.warning("MOCK_API_CALLS is set to True. API calls to Google Maps will NOT be executed, and randomized times will be returned instead.")
        
    await scheduler.start()
    
    yield
    
    # Shutdown: Stop the scheduler task cleanly
    logger.info("--- Shutting down Traffic Data Monitor Application ---")
    await scheduler.stop()

# Initialize API server
app = FastAPI(
    title="Directions Chron API",
    description="API for managing and querying traffic directions data",
    lifespan=lifespan
)
app.include_router(routes_router)
app.include_router(aliases_router)
if __name__ == "__main__":
    # When run directly, start the uvicorn server handling this FastAPI app locally
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
