"""
@fileoverview BookTalk - Text-to-Audiobook Conversion Application, Main FastAPI entry point
@author Timothy Mallory <windsage@live.com>
@license Apache-2.0
@copyright 2026 Timothy Mallory <windsage@live.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
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
