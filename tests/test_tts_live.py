import pytest

from src.core.tts_engine import init_tts_engine


@pytest.mark.live_tts
def test_live_tts_engine_generates_audio():
    engine = init_tts_engine()

    try:
        audio, sample_rate = engine.generate_speech("This is a live TTS smoke test.", "af_heart", 1.0)
    finally:
        engine.cleanup()

    assert sample_rate == 24000
    assert len(audio) > 0
