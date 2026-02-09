"""
Tests for the TTS engine (real Kokoro model).

All tests in this module are marked @pytest.mark.slow because they require
loading and running the Kokoro-82M model.

Run only these:  pytest tests/test_tts_engine.py -v
Skip these:      pytest -m "not slow"
"""

import os
import pytest
import numpy as np

from src.core.tts_engine import PRESET_VOICES, TTSEngine


# Mark every test in this module as 'slow'
pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# Voice catalogue (no model needed)
# ---------------------------------------------------------------------------


class TestVoiceCatalogue:
    def test_count(self):
        assert len(PRESET_VOICES) == 28

    def test_required_fields(self):
        for v in PRESET_VOICES:
            assert v.id, f"Voice missing id: {v}"
            assert v.name, f"Voice missing name: {v}"
            assert v.description, f"Voice missing description: {v}"
            assert v.gender in ("male", "female"), f"Unexpected gender: {v.gender}"

    def test_id_prefixes(self):
        prefixes = {v.id[:2] for v in PRESET_VOICES}
        assert prefixes == {"af", "am", "bf", "bm"}


# ---------------------------------------------------------------------------
# Engine initialisation
# ---------------------------------------------------------------------------


class TestEngineInit:
    def test_initializes(self, tts_engine):
        assert tts_engine.is_initialized()

    def test_get_available_voices(self, tts_engine):
        voices = tts_engine.get_available_voices()
        assert len(voices) == 28


# ---------------------------------------------------------------------------
# Speech generation
# ---------------------------------------------------------------------------


class TestGenerateSpeech:
    def test_returns_audio_array(self, tts_engine):
        audio, sr = tts_engine.generate_speech("Hello world.", "af_heart")
        assert isinstance(audio, np.ndarray)
        assert sr == 24000
        assert len(audio) > 0

    def test_different_voices(self, tts_engine):
        audio_f, sr_f = tts_engine.generate_speech("Test.", "af_heart")
        audio_m, sr_m = tts_engine.generate_speech("Test.", "bm_lewis")
        assert len(audio_f) > 0
        assert len(audio_m) > 0
        assert sr_f == sr_m == 24000

    def test_speed_variation(self, tts_engine):
        """Faster speed should produce shorter audio."""
        text = "This is a sentence to test speed variation."
        audio_normal, _ = tts_engine.generate_speech(text, "af_heart", speed=1.0)
        audio_fast, _ = tts_engine.generate_speech(text, "af_heart", speed=2.0)
        # 2x speed should be noticeably shorter
        assert len(audio_fast) < len(audio_normal) * 0.85

    def test_longer_text(self, tts_engine):
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "Pack my box with five dozen liquor jugs. "
            "How vexingly quick daft zebras jump."
        )
        audio, sr = tts_engine.generate_speech(text, "af_heart")
        # Should be at least a few seconds of audio (24000 samples/sec)
        assert len(audio) > sr * 2  # > 2 seconds


class TestGenerateSample:
    def test_returns_audio(self, tts_engine):
        audio, sr = tts_engine.generate_sample("af_heart")
        assert isinstance(audio, np.ndarray)
        assert sr == 24000
        assert len(audio) > 0


# ---------------------------------------------------------------------------
# End-to-end: TTS → encode → valid file on disk
# ---------------------------------------------------------------------------


class TestTTSThenEncode:
    def test_full_pipeline(self, tts_engine, tmp_path):
        """Generate speech and encode it to a WAV file on disk."""
        from src.core.encoder import encode_audio, EncoderSettings

        text = "This is a full end-to-end test of the speech pipeline."
        audio, sr = tts_engine.generate_speech(text, "af_heart", speed=1.0)

        out_path = str(tmp_path / "output.wav")
        result = encode_audio(audio, sr, out_path, EncoderSettings(format="wav"))

        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

        # Verify the WAV is readable
        from scipy.io import wavfile

        read_sr, data = wavfile.read(result)
        assert read_sr == 24000
        assert len(data) > 0
