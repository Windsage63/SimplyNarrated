"""
@fileoverview SimplyNarrated - TTS Engine, Wrapper for Kokoro-82M text-to-speech model
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
import sys
import logging
import threading
import warnings
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Suppress annoying PyTorch and Library warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.rnn")
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.utils.weight_norm")

# Directory containing local voice .pt files
VOICES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "voices")

# Ensure the embedded spaCy model (models/en_core_web_sm) is discoverable.
# The embedded Python environment lacks a standalone `pip` command, so spaCy's
# automatic download cannot work.  By placing the models/ directory on sys.path
# the model package is importable and spaCy skips the download entirely.
_MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models"))
if os.path.isdir(_MODELS_DIR) and _MODELS_DIR not in sys.path:
    sys.path.insert(0, _MODELS_DIR)

# Default repository ID for Kokoro base model
REPO_ID = "hexgrad/Kokoro-82M"


@dataclass
class VoiceConfig:
    """Configuration for a voice."""

    id: str
    name: str
    description: str
    gender: str
    model: str = "kokoro"


class BaseTTSModel(ABC):
    """Abstract interface for a TTS model backend."""

    name: str

    @abstractmethod
    def load(self) -> None:
        """Load the model into memory."""

    @abstractmethod
    def unload(self) -> None:
        """Release model resources."""

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return whether the model is ready for inference."""

    @abstractmethod
    def get_voices(self) -> List[VoiceConfig]:
        """Return the model's available voices."""

    @abstractmethod
    def generate_speech(self, text: str, voice_id: str) -> Tuple[np.ndarray, int]:
        """Generate speech for the given text and voice."""

    @abstractmethod
    def generate_sample(self, voice_id: str) -> Tuple[np.ndarray, int]:
        """Generate a preview sample for the given voice."""


# Available Kokoro voices - American (🇺🇸) and British (🇬🇧) English
# American English: af_* (female), am_* (male)
# British English: bf_* (female), bm_* (male)
PRESET_VOICES: List[VoiceConfig] = [
    # American Female (af_)
    VoiceConfig("af_heart", "🇺🇸 Heart", "Warm & Expressive", "female"),
    VoiceConfig("af_alloy", "🇺🇸 Alloy", "Neutral & Balanced", "female"),
    VoiceConfig("af_aoede", "🇺🇸 Aoede", "Melodic & Artistic", "female"),
    VoiceConfig("af_bella", "🇺🇸 Bella", "Bright & Friendly", "female"),
    VoiceConfig("af_jessica", "🇺🇸 Jessica", "Lively & Engaging", "female"),
    VoiceConfig("af_kore", "🇺🇸 Kore", "Youthful & Fresh", "female"),
    VoiceConfig("af_nicole", "🇺🇸 Nicole", "Clear & Professional", "female"),
    VoiceConfig("af_nova", "🇺🇸 Nova", "Dynamic & Modern", "female"),
    VoiceConfig("af_river", "🇺🇸 River", "Flowing & Natural", "female"),
    VoiceConfig("af_sarah", "🇺🇸 Sarah", "Soft & Gentle", "female"),
    VoiceConfig("af_sky", "🇺🇸 Sky", "Light & Airy", "female"),
    # American Male (am_)
    VoiceConfig("am_adam", "🇺🇸 Adam", "Smooth & Confident", "male"),
    VoiceConfig("am_echo", "🇺🇸 Echo", "Resonant & Clear", "male"),
    VoiceConfig("am_eric", "🇺🇸 Eric", "Strong & Assertive", "male"),
    VoiceConfig("am_fenrir", "🇺🇸 Fenrir", "Deep & Powerful", "male"),
    VoiceConfig("am_liam", "🇺🇸 Liam", "Casual & Friendly", "male"),
    VoiceConfig("am_michael", "🇺🇸 Michael", "Deep & Authoritative", "male"),
    VoiceConfig("am_onyx", "🇺🇸 Onyx", "Rich & Bold", "male"),
    VoiceConfig("am_puck", "🇺🇸 Puck", "Playful & Quick", "male"),
    VoiceConfig("am_santa", "🇺🇸 Santa", "Warm & Jolly", "male"),
    # British Female (bf_)
    VoiceConfig("bf_alice", "🇬🇧 Alice", "Refined & Elegant", "female"),
    VoiceConfig("bf_emma", "🇬🇧 Emma", "British & Warm", "female"),
    VoiceConfig("bf_isabella", "🇬🇧 Isabella", "Sophisticated & Poised", "female"),
    VoiceConfig("bf_lily", "🇬🇧 Lily", "Gentle & Sweet", "female"),
    # British Male (bm_)
    VoiceConfig("bm_daniel", "🇬🇧 Daniel", "Gentle & Articulate", "male"),
    VoiceConfig("bm_fable", "🇬🇧 Fable", "Storyteller & Narrative", "male"),
    VoiceConfig("bm_george", "🇬🇧 George", "British & Calm", "male"),
    VoiceConfig("bm_lewis", "🇬🇧 Lewis", "Formal & Distinguished", "male"),
]


class KokoroTTSModel(BaseTTSModel):
    """Text-to-Speech engine using Kokoro-82M."""

    name = "kokoro"

    def __init__(self, device: Optional[str] = None):
        """Initialize the TTS engine."""
        self._pipelines: Dict[str, object] = {}  # keyed by lang_code 'a' or 'b'
        self._shared_model = None  # Shared KModel instance to save memory
        self._initialized = False
        self._device = device  # Kokoro handles device selection automatically
        self._init_lock = threading.Lock()

    @staticmethod
    def _lang_code_for_voice(voice_id: str) -> str:
        """Derive Kokoro lang_code from voice ID prefix.

        af_*/am_* -> 'a' (American English)
        bf_*/bm_* -> 'b' (British English)
        """
        if voice_id.startswith(("bf_", "bm_")):
            return "b"
        return "a"

    @staticmethod
    def _resolve_voice(voice_id: str) -> str:
        """Return local .pt path if available, otherwise the bare voice ID."""
        local_path = os.path.join(VOICES_DIR, f"{voice_id}.pt")
        if os.path.isfile(local_path):
            return local_path
        return voice_id

    def _get_pipeline(self, voice_id: str):
        """Get (or lazily create) the KPipeline for the given voice."""
        lang_code = self._lang_code_for_voice(voice_id)
        with self._init_lock:
            if lang_code in self._pipelines:
                return self._pipelines[lang_code]

            from kokoro import KPipeline

            label = "American" if lang_code == "a" else "British"

            # If we don't have a shared model yet, creating the first pipeline will load it.
            # Subsequent pipelines use the already-loaded shared model.
            if self._shared_model is None:
                logger.info("Loading Kokoro-82M (base model)...")
                pipeline = KPipeline(lang_code=lang_code, repo_id=REPO_ID, device=self._device)
                self._shared_model = pipeline.model
                logger.info("Kokoro-82M (base model) loaded successfully!")
                logger.info("Initializing %s English G2P rules...", label)
            else:
                logger.info("Initializing %s English G2P rules (sharing base model)...", label)
                # Reuse the model for other languages (fixes British pronunciation rules)
                pipeline = KPipeline(
                    lang_code=lang_code,
                    model=self._shared_model,
                    repo_id=REPO_ID,
                    device=self._device,
                )

            self._pipelines[lang_code] = pipeline
            logger.info("%s English G2P rules initialized!", label)
            self._initialized = True

            return pipeline

    def load(self) -> None:
        """Pre-load the American English pipeline."""
        if self._initialized:
            return
        self._get_pipeline("af_heart")  # triggers 'a' pipeline creation

    def initialize(self) -> None:
        """Backward-compatible alias for Kokoro loading."""
        self.load()

    def preload_runtime_assets(self) -> None:
        """Preload the shared Kokoro-82M base model once and both English pipelines."""
        self._get_pipeline("af_heart")
        self._get_pipeline("bf_alice")

    def is_loaded(self) -> bool:
        """Check if at least one pipeline is loaded."""
        return self._initialized

    def is_initialized(self) -> bool:
        """Backward-compatible alias for Kokoro readiness."""
        return self.is_loaded()

    def get_voices(self) -> List[VoiceConfig]:
        """Get list of available voices."""
        return PRESET_VOICES

    def get_available_voices(self) -> List[VoiceConfig]:
        """Backward-compatible alias for Kokoro voice lookup."""
        return self.get_voices()

    def generate_speech(
        self,
        text: str,
        voice_id: str = "af_heart",
    ) -> Tuple[np.ndarray, int]:
        """
        Generate speech from text.

        Args:
            text: The text to convert to speech
            voice_id: Kokoro voice ID (e.g., 'af_heart', 'am_adam')

        Returns:
            Tuple of (audio_array, sample_rate)
        """
        if not self._initialized:
            self.load()

        try:
            # Select the correct pipeline for this voice's language
            pipeline = self._get_pipeline(voice_id)
            # Use local .pt file if available, otherwise Kokoro downloads from HF
            voice = self._resolve_voice(voice_id)

            # Generate audio using Kokoro
            # Returns generator of (graphemes, phonemes, audio) tuples
            generator = pipeline(text, voice=voice, speed=1.0)

            # Collect all audio chunks
            audio_chunks = []
            for _, _, audio_chunk in generator:
                audio_chunks.append(audio_chunk)

            # Concatenate all chunks
            if audio_chunks:
                audio = np.concatenate(audio_chunks)
            else:
                raise RuntimeError("No audio generated")

            # Kokoro uses 24kHz sample rate
            sample_rate = 24000

            return audio, sample_rate

        except Exception as e:
            logger.exception("Speech generation failed")
            raise RuntimeError(f"Speech generation failed: {e}")

    def generate_sample(self, voice_id: str) -> Tuple[np.ndarray, int]:
        """Generate a sample for voice preview."""
        sample_text = (
            "Hello! This is a sample of my voice. I hope you like how I sound."
        )
        return self.generate_speech(sample_text, voice_id)

    def unload(self) -> None:
        """Release model resources."""
        if self._pipelines:
            for key in list(self._pipelines):
                del self._pipelines[key]
            self._pipelines.clear()
            self._shared_model = None
            self._initialized = False

            # Clear CUDA cache if available
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    def cleanup(self) -> None:
        """Backward-compatible alias for Kokoro cleanup."""
        self.unload()


class TTSModelManager:
    """Singleton-like manager for available TTS backends."""

    def __init__(self, device: Optional[str] = None, default_model: str = "kokoro"):
        self._device = device
        self._default_model = default_model
        self._active_model: Optional[BaseTTSModel] = None
        self._model_registry: Dict[str, type] = {
            "kokoro": KokoroTTSModel,
        }
        self._instances: Dict[str, BaseTTSModel] = {}

    def get_available_model_names(self) -> List[str]:
        """Return the registered model identifiers."""
        return list(self._model_registry.keys())

    def switch_model(self, model_name: str) -> BaseTTSModel:
        """Switch the active model, unloading the previous model if needed."""
        if model_name not in self._model_registry:
            raise ValueError(f"Unsupported TTS model: {model_name}")

        if self._active_model is not None and self._active_model.name == model_name:
            if not self._active_model.is_loaded():
                self._active_model.load()
            return self._active_model

        if self._active_model is not None:
            self._active_model.unload()

        model = self._instances.get(model_name)
        if model is None:
            model = self._model_registry[model_name](device=self._device)
            self._instances[model_name] = model

        if not model.is_loaded():
            model.load()

        self._active_model = model
        return model

    def get_active_model(self) -> BaseTTSModel:
        """Return the current model, loading the default model if required."""
        if self._active_model is None:
            return self.switch_model(self._default_model)
        if not self._active_model.is_loaded():
            self._active_model.load()
        return self._active_model


# Backward-compatible alias while Phase 1 removes direct callers.
TTSEngine = KokoroTTSModel


_tts_manager: Optional[TTSModelManager] = None


def get_tts_manager() -> TTSModelManager:
    """Get the global TTS model manager instance."""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSModelManager()
    return _tts_manager


def init_tts_manager(device: Optional[str] = None) -> TTSModelManager:
    """Initialize the global TTS model manager."""
    global _tts_manager
    _tts_manager = TTSModelManager(device=device)
    return _tts_manager


def get_tts_engine() -> BaseTTSModel:
    """Backward-compatible accessor for the active TTS model."""
    return get_tts_manager().get_active_model()


def init_tts_engine(device: Optional[str] = None) -> BaseTTSModel:
    """Backward-compatible initializer for the active TTS model."""
    return init_tts_manager(device=device).get_active_model()
