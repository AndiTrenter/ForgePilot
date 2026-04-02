"""
ForgePilot Server v3.0
Modernized with Modular Architecture
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import (
    get_config,
    get_database,
    connect_database,
    disconnect_database
)

# Import API routers
from api.v1 import settings_router, tasks_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan-Kontext f\u00fcr Startup/Shutdown"""
    config = get_config()
    logger.info(f"Starting ForgePilot API v{config.version}")
    
    # Connect to database
    try:
        await connect_database()
        logger.info("\u2705 Database connected")
    except Exception as e:
        logger.error(f"\u274c Database connection failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down ForgePilot API")
    await disconnect_database()


# Create FastAPI app
config = get_config()
app = FastAPI(
    title="ForgePilot API",
    version=config.version,
    description="Agentic Delivery Operating System",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": config.version,
        "environment": config.environment
    }

# Include new API v1 routers
app.include_router(settings_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")

# TODO: Legacy routes from old server.py will be migrated incrementally
# For now, we need to keep the old server.py running alongside this

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server_v3:app",
        host=config.host,
        port=config.port,
        reload=config.reload
    )
