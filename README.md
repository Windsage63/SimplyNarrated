# SimplyNarrated

**SimplyNarrated** is a local web application that converts books and text documents (`.txt`, `.md`, `.pdf`) into audiobooks saved as MP3 chapter files. Designed for non-technical users, it provides a polished multi-page interface with a landing page, file upload/configuration screen, conversion progress tracker, audiobook player, and user dashboard.

The system uses the **Kokoro-82M** model running locally on GPU for high-quality, expressive speech synthesis.

## Features

- **Local Inference**: Uses Kokoro-82M TTS model running locally. Includes pre-distributed voice tensors for zero-download voice switching.
- **Dual-Region Support**: Automatic selection of American ('a') or British ('b') G2P rules based on voice selection.
- **Memory Efficient**: Shares a single base model across multiple language pipelines to save RAM.
- **Multiple Formats**: Supports uploading TXT, MD, and PDF files.
- **Smart Chunking**: Splits text into natural chapters or segments.
- **Audiobook Player**: Built-in player with progress tracking and bookmarks.
- **Library Management**: Dashboard to manage your converted books.
- **Modern UI**: Polished interface with dark mode support.

## Installation

### Prerequisites

- Python 3.12
- NVIDIA GPU with CUDA support (recommended for performance)

### Setup Steps

1. **Install PyTorch with CUDA support** (Important: do this first):

   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
   ```

2. **Install project dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the server**:

   ```bash
   uvicorn src.main:app --reload
   ```

2. **Open the application**:
   Navigate to `http://localhost:8000` in your web browser.

## Project Structure

- `src/`: Source code
  - `api/`: FastAPI routes and endpoints
  - `core/`: Core logic (TTS engine, parser, chunker)
  - `models/`: Pydantic data models
- `data/`: Local storage for uploads and library
- `docs/`: Documentation files
- `static/`: Frontend assets
  - `voices/`: Local voice model tensors (`.pt`)
  - `voices/audio/`: Cached voice sample previews (`.mp3`)
- `tests/`: Unit and integration tests

## Documentation

- [API Reference](docs/API-Reference.md)
- [Architecture Plan](plans/architect_plan.md)

## Acknowledgements

**SimplyNarrated** uses the Kokoro TTS Engine developed by Hexgrad. This project is built on top of the following resources:

- **Kokoro-82M Model**: A high-quality, lightweight TTS model. Available on [Hugging Face](https://huggingface.co/hexgrad/Kokoro-82M).
- **Kokoro Inference Library**: The official Python library for Kokoro inference. Available on [GitHub](https://github.com/hexgrad/kokoro).
