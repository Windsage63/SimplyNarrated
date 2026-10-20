"""
@fileoverview SimplyNarrated - Text-to-Audiobook Conversion Application, Main FastAPI entry point
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

import os
import logging
from logging.handlers import RotatingFileHandler

# Apply the same safe default when launched directly with uvicorn.
# This must run before imports that initialize Transformers/Hugging Face.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from src.api.routes import router as api_router
from src.core.job_manager import init_job_manager
from src.core.library import init_library_manager

# Ensure static-ffmpeg binaries are on PATH for pydub/subprocess
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass  # Fall through to system ffmpeg


# Get the base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
LIBRARY_DIR = os.path.join(DATA_DIR, "library")
APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup: ensure data directories exist
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
    os.makedirs(LIBRARY_DIR, exist_ok=True)

    # Write application errors before they propagate to console handlers, so a
    # disconnected terminal cannot hide the original conversion traceback.
    log_dir = os.path.join(DATA_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    error_handler = RotatingFileHandler(
        os.path.join(log_dir, "simplynarrated.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    ))
    app_logger = logging.getLogger("src")
    app_logger.addHandler(error_handler)

    try:
        init_job_manager(DATA_DIR)
        init_library_manager(LIBRARY_DIR)
        yield
    finally:
        app_logger.removeHandler(error_handler)
        error_handler.close()


app = FastAPI(
    title="SimplyNarrated",
    description="Convert books and text documents to audiobooks using AI",
    version=APP_VERSION,
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
    return {"status": "healthy", "version": APP_VERSION}
