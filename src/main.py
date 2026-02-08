"""
BookTalk - Text-to-Audiobook Conversion Application
Main FastAPI entry point
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from src.api.routes import router as api_router
from src.core.job_manager import init_job_manager
from src.core.library import init_library_manager


# Get the base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
LIBRARY_DIR = os.path.join(DATA_DIR, "library")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: ensure data directories exist
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
    os.makedirs(LIBRARY_DIR, exist_ok=True)

    # Initialize managers
    init_job_manager(DATA_DIR)
    init_library_manager(LIBRARY_DIR)

    yield

    # Shutdown: cleanup if needed
    pass


app = FastAPI(
    title="BookTalk",
    description="Convert books and text documents to audiobooks using AI",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def serve_index():
    """Serve the main SPA index.html."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}
