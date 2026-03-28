"""
Tests for TTSEngine concurrency behavior without loading the real Kokoro model.
"""

import sys
import time
import types
import threading
from concurrent.futures import ThreadPoolExecutor

from src.core.tts_engine import TTSEngine


class TestTTSEngineConcurrency:
    def test_concurrent_pipeline_initialization_is_serialized(self, monkeypatch):
        class FakePipeline:
            created = 0
            created_lock = threading.Lock()

            def __init__(self, lang_code, repo_id=None, device=None, model=None):
                time.sleep(0.05)
                with FakePipeline.created_lock:
                    FakePipeline.created += 1
                self.lang_code = lang_code
                self.model = model or object()

        monkeypatch.setitem(sys.modules, "kokoro", types.SimpleNamespace(KPipeline=FakePipeline))

        engine = TTSEngine()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(engine._get_pipeline, "af_heart") for _ in range(5)]

        results = [future.result() for future in futures]
        assert FakePipeline.created == 1
        assert len({id(result) for result in results}) == 1
        assert engine.is_initialized()

    def test_preload_runtime_assets_downloads_both_english_pipelines(self, monkeypatch):
        class FakePipeline:
            created = 0

            def __init__(self, lang_code, repo_id=None, device=None, model=None):
                FakePipeline.created += 1
                self.lang_code = lang_code
                self.model = model or object()

        monkeypatch.setitem(sys.modules, "kokoro", types.SimpleNamespace(KPipeline=FakePipeline))

        engine = TTSEngine()
        engine.preload_runtime_assets()

        assert FakePipeline.created == 2
        assert set(engine._pipelines) == {"a", "b"}
        assert engine._pipelines["a"].model is engine._pipelines["b"].model
        assert engine.is_initialized()
