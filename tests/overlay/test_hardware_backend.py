"""Tests for hermes_cli.hardware_backend."""

from __future__ import annotations

from hermes_cli import hardware_backend as hb


def test_looks_like_cuda_lib_error_matches_missing_lib():
    exc = RuntimeError("Library libcublas.so.12 is not found or cannot be loaded")
    assert hb.looks_like_cuda_lib_error(exc) is True


def test_looks_like_cuda_lib_error_ignores_oom():
    exc = RuntimeError("CUDA out of memory")
    assert hb.looks_like_cuda_lib_error(exc) is False


def test_build_onnx_provider_attempts_order(monkeypatch):
    monkeypatch.setattr(
        hb,
        "get_onnxruntime_available_providers",
        lambda: [
            "CPUExecutionProvider",
            "DmlExecutionProvider",
            "CUDAExecutionProvider",
        ],
    )
    attempts = hb.build_onnx_provider_attempts()
    names = [name for name, _ in attempts]
    assert names == [hb.BackendName.CUDA, hb.BackendName.DIRECTML, hb.BackendName.CPU]


def test_select_torch_device_respects_cpu():
    device, backend = hb.select_torch_device("cpu")
    assert device == "cpu"
    assert backend == hb.BackendName.CPU


def test_resolve_whisper_device_from_env_auto_cpu(monkeypatch):
    monkeypatch.setattr(hb, "probe_torch_cuda", lambda: False)
    device, compute = hb.resolve_whisper_device_from_env("auto")
    assert device == "cpu"
    assert compute == "int8"


def test_resolve_whisper_device_from_env_cuda(monkeypatch):
    monkeypatch.setattr(hb, "probe_torch_cuda", lambda: True)
    device, compute = hb.resolve_whisper_device_from_env("auto")
    assert device == "cuda"
    assert compute == "float16"


def test_probe_startup_backends_includes_whisper_note(monkeypatch):
    monkeypatch.setattr(hb, "probe_torch_cuda", lambda: False)
    monkeypatch.setattr(hb, "get_onnxruntime_available_providers", lambda: ["CPUExecutionProvider"])
    lines = hb.probe_startup_backends()
    joined = "\n".join(lines)
    assert "faster-whisper" in joined
    assert "DirectML not supported" in joined


def test_select_torch_device_cuda_unavailable_falls_back(monkeypatch):
    monkeypatch.setattr(hb, "probe_torch_cuda", lambda: False)
    device, backend = hb.select_torch_device("cuda")
    assert device == "cpu"
    assert backend == hb.BackendName.CPU


def test_load_faster_whisper_auto_falls_back_to_cpu(monkeypatch):
    class FakeWhisper:
        def __init__(self, model_name, device, compute_type):
            self.model_name = model_name
            self.device = device
            self.compute_type = compute_type

    calls: list[tuple[str, str, str]] = []

    def fake_ctor(model_name, device, compute_type):
        calls.append((model_name, device, compute_type))
        if device in {"cuda", "auto"} and len(calls) == 1:
            raise RuntimeError("cannot be loaded")
        return FakeWhisper(model_name, device, compute_type)

    monkeypatch.setattr("faster_whisper.WhisperModel", fake_ctor)
    hb._selections.clear()
    model = hb.load_faster_whisper_model("tiny", preferred_device="auto")
    assert model.device == "cpu"
    assert len(calls) == 2


def test_reset_hardware_backend_cache_clears_onnx_cache(monkeypatch):
    hb.reset_hardware_backend_cache()
    monkeypatch.setattr(hb, "get_onnxruntime_available_providers", lambda: ["CPUExecutionProvider"])
    first = hb.get_onnxruntime_available_providers()
    hb._onnx_providers_cache = ["CachedProvider"]
    hb.reset_hardware_backend_cache()
    second = hb.get_onnxruntime_available_providers()
    assert first == ["CPUExecutionProvider"]
    assert second == ["CPUExecutionProvider"]
