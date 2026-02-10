"""
@fileoverview BookTalk - TTS Engine, Wrapper for Kokoro-82M text-to-speech model
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
import warnings
import numpy as np
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

# Suppress annoying PyTorch and Library warnings
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.rnn")
warnings.filterwarnings("ignore", category=FutureWarning, module="torch.nn.utils.weight_norm")

# Directory containing local voice .pt files
VOICES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static", "voices")
# Default repository ID for Kokoro base model
REPO_ID = "hexgrad/Kokoro-82M"


@dataclass
class VoiceConfig:
    """Configuration for a voice."""

    id: str
    name: str
    description: str
    gender: str


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


class TTSEngine:
    """Text-to-Speech engine using Kokoro-82M."""

    def __init__(self, device: Optional[str] = None):
        """Initialize the TTS engine."""
        self._pipelines: Dict[str, object] = {}  # keyed by lang_code 'a' or 'b'
        self._shared_model = None  # Shared KModel instance to save memory
        self._initialized = False
        self._device = device  # Kokoro handles device selection automatically

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
        if lang_code not in self._pipelines:
            from kokoro import KPipeline

            label = "American" if lang_code == "a" else "British"
            
            # If we don't have a shared model yet, creating the first pipeline will load it.
            # Subsequent pipelines use the already-loaded shared model.
            if self._shared_model is None:
                print("Loading Kokoro-82M (base model)...")
                pipeline = KPipeline(lang_code=lang_code, repo_id=REPO_ID, device=self._device)
                self._shared_model = pipeline.model
                print("Kokoro-82M (base model) loaded successfully!")
                print(f"Initializing {label} English G2P rules...")
            else:
                print(f"Initializing {label} English G2P rules (sharing base model)...")
                # Reuse the model for other languages (fixes British pronunciation rules)
                pipeline = KPipeline(
                    lang_code=lang_code, 
                    model=self._shared_model, 
                    repo_id=REPO_ID,
                    device=self._device
                )
            
            self._pipelines[lang_code] = pipeline
            print(f"{label} English G2P rules initialized!")
            self._initialized = True
            
        return self._pipelines[lang_code]

    def initialize(self) -> None:
        """Pre-load the American English pipeline."""
        if self._initialized:
            return
        self._get_pipeline("af_heart")  # triggers 'a' pipeline creation

    def is_initialized(self) -> bool:
        """Check if at least one pipeline is loaded."""
        return self._initialized

    def get_available_voices(self) -> List[VoiceConfig]:
        """Get list of available voices."""
        return PRESET_VOICES

    def generate_speech(
        self,
        text: str,
        voice_id: str = "af_heart",
        speed: float = 1.0,
    ) -> Tuple[np.ndarray, int]:
        """
        Generate speech from text.

        Args:
            text: The text to convert to speech
            voice_id: Kokoro voice ID (e.g., 'af_heart', 'am_adam')
            speed: Playback speed multiplier (0.5 to 2.0)

        Returns:
            Tuple of (audio_array, sample_rate)
        """
        if not self._initialized:
            self.initialize()

        try:
            # Select the correct pipeline for this voice's language
            pipeline = self._get_pipeline(voice_id)
            # Use local .pt file if available, otherwise Kokoro downloads from HF
            voice = self._resolve_voice(voice_id)

            # Generate audio using Kokoro
            # Returns generator of (graphemes, phonemes, audio) tuples
            generator = pipeline(text, voice=voice, speed=speed)

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
            import traceback

            traceback.print_exc()
            raise RuntimeError(f"Speech generation failed: {e}")

    def generate_sample(
        self, voice_id: str, duration_seconds: float = 3.0
    ) -> Tuple[np.ndarray, int]:
        """Generate a sample for voice preview."""
        sample_text = (
            "Hello! This is a sample of my voice. I hope you like how I sound."
        )
        return self.generate_speech(sample_text, voice_id)

    def cleanup(self) -> None:
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


# Global TTS engine instance
_tts_engine: Optional[TTSEngine] = None


def get_tts_engine() -> TTSEngine:
    """Get the global TTS engine instance."""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine


def init_tts_engine(device: Optional[str] = None) -> TTSEngine:
    """Initialize the global TTS engine."""
    global _tts_engine
    _tts_engine = TTSEngine(device)
    return _tts_engine
