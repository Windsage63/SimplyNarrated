"""
BookTalk - TTS Engine
Wrapper for Kokoro-82M text-to-speech model
"""

import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class VoiceConfig:
    """Configuration for a voice."""

    id: str
    name: str
    description: str
    gender: str


# Available Kokoro voices
# American English: af_* (female), am_* (male)
# British English: bf_* (female), bm_* (male)
PRESET_VOICES: List[VoiceConfig] = [
    VoiceConfig("af_heart", "Heart", "Warm & Expressive", "female"),
    VoiceConfig("af_bella", "Bella", "Bright & Friendly", "female"),
    VoiceConfig("af_nicole", "Nicole", "Clear & Professional", "female"),
    VoiceConfig("af_sarah", "Sarah", "Soft & Gentle", "female"),
    VoiceConfig("am_adam", "Adam", "Smooth & Confident", "male"),
    VoiceConfig("am_michael", "Michael", "Deep & Authoritative", "male"),
    VoiceConfig("bf_emma", "Emma", "British & Warm", "female"),
    VoiceConfig("bm_george", "George", "British & Calm", "male"),
]


class TTSEngine:
    """Text-to-Speech engine using Kokoro-82M."""

    def __init__(self, device: Optional[str] = None):
        """Initialize the TTS engine."""
        self.pipeline = None
        self._initialized = False
        self._device = device  # Kokoro handles device selection automatically

    def initialize(self) -> None:
        """Load the Kokoro model."""
        if self._initialized:
            return

        try:
            from kokoro import KPipeline

            print("Loading Kokoro-82M...")
            # 'a' = American English, 'b' = British English
            self.pipeline = KPipeline(lang_code='a')
            self._initialized = True
            print("Kokoro-82M loaded successfully!")

        except Exception as e:
            print(f"Failed to load Kokoro model: {e}")
            raise RuntimeError(f"Could not initialize TTS engine: {e}")

    def is_initialized(self) -> bool:
        """Check if the model is loaded."""
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
            # Generate audio using Kokoro
            # Returns generator of (graphemes, phonemes, audio) tuples
            generator = self.pipeline(text, voice=voice_id, speed=speed)
            
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
        if self.pipeline is not None:
            del self.pipeline
            self.pipeline = None
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
