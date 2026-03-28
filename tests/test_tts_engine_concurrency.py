"""
Tests for TTSEngine concurrency behavior without loading the real Kokoro model.
"""

from pathlib import Path
import sys
import time
import types
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

import src.core.tts_engine as tts_module
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


class TestTTSEnginePipBootstrap:
    def test_missing_pip_bootstraps_before_pipeline_creation(self, monkeypatch):
        class FakePipeline:
            def __init__(self, lang_code, repo_id=None, device=None, model=None):
                self.lang_code = lang_code
                self.model = model or object()

        pip_checks = {"count": 0}
        bootstrap_calls = []

        def fake_find_spec(name):
            if name != "pip":
                return None
            pip_checks["count"] += 1
            return None if pip_checks["count"] == 1 else object()

        def fake_urlretrieve(url, filename):
            bootstrap_calls.append(("download", url, filename))
            Path(filename).write_text("# get-pip placeholder", encoding="utf-8")
            return filename, None

        def fake_run(cmd, check, capture_output, text):
            bootstrap_calls.append(("run", cmd, check, capture_output, text))
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(tts_module.importlib.util, "find_spec", fake_find_spec)
        monkeypatch.setattr(tts_module.urllib.request, "urlretrieve", fake_urlretrieve)
        monkeypatch.setattr(
            tts_module.importlib,
            "invalidate_caches",
            lambda: bootstrap_calls.append(("invalidate",)),
        )
        monkeypatch.setattr(tts_module.subprocess, "run", fake_run)
        monkeypatch.setitem(sys.modules, "kokoro", types.SimpleNamespace(KPipeline=FakePipeline))

        engine = TTSEngine()
        pipeline = engine._get_pipeline("af_heart")

        assert isinstance(pipeline, FakePipeline)
        assert bootstrap_calls[0][0] == "download"
        assert bootstrap_calls[1][0] == "run"
        assert bootstrap_calls[1][1][0] == tts_module.sys.executable
        assert bootstrap_calls[1][1][1].endswith("get-pip.py")
        assert engine.is_initialized()

    def test_bootstrap_failure_raises_clear_error(self, monkeypatch):
        monkeypatch.setattr(tts_module.importlib.util, "find_spec", lambda name: None)
        monkeypatch.setattr(
            tts_module.urllib.request,
            "urlretrieve",
            lambda url, filename: (_ for _ in ()).throw(OSError("offline")),
        )

        engine = TTSEngine()
        with pytest.raises(RuntimeError, match="Automatic pip bootstrap failed"):
            engine._get_pipeline("af_heart")
