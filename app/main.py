from fastapi import FastAPI
import logging

from .core.config import settings
from .api.endpoints import router as api_router
from .db.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Create application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API for detecting prompt injection attacks",
)

# Initialize database on startup
@app.on_event("startup")
async def startup_db_client():
    try:
        init_db()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Application can still start without DB

# Include routers
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Prompt Injection Detection API",
        "version": settings.APP_VERSION,
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
