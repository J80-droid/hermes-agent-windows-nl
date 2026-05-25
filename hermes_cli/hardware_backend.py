"""Hardware acceleration selection for local inference (Windows-first).

Fallback chains:
  - faster-whisper (ctranslate2): CUDA/auto -> CPU (DirectML not supported)
  - ONNX Runtime (Piper TTS): CUDA -> DirectML -> CPU
  - PyTorch (NeuTTS): CUDA -> CPU (MPS on macOS when available)
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

_CUDA_LIB_ERROR_MARKERS = (
    "libcublas",
    "libcudnn",
    "libcudart",
    "cublas64",
    "cudnn64",
    "cudart64",
    "cannot be loaded",
    "cannot open shared object",
    "no kernel image is available",
    "no CUDA-capable device",
    "CUDA driver version is insufficient",
)

_onnx_providers_cache: list[str] | None = None


class BackendName(str, Enum):
    CUDA = "cuda"
    DIRECTML = "directml"
    CPU = "cpu"
    MPS = "mps"
    AUTO = "auto"


@dataclass(frozen=True)
class BackendSelection:
    component: str
    backend: BackendName
    detail: str


_selections: dict[str, BackendSelection] = {}
_startup_summary_printed = False


def is_windows() -> bool:
    return sys.platform == "win32"


def looks_like_cuda_lib_error(exc: BaseException) -> bool:
    msg = str(exc)
    return any(marker in msg for marker in _CUDA_LIB_ERROR_MARKERS)


def _onnxruntime_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("onnxruntime") is not None
    except Exception:
        return False


def get_onnxruntime_available_providers() -> list[str]:
    global _onnx_providers_cache
    if _onnx_providers_cache is not None:
        return list(_onnx_providers_cache)
    if not _onnxruntime_available():
        _onnx_providers_cache = []
        return []
    try:
        import onnxruntime as ort

        _onnx_providers_cache = list(ort.get_available_providers())
        return list(_onnx_providers_cache)
    except Exception:
        _onnx_providers_cache = []
        return []


def probe_cuda_onnx() -> bool:
    return "CUDAExecutionProvider" in get_onnxruntime_available_providers()


def probe_directml_onnx() -> bool:
    providers = get_onnxruntime_available_providers()
    return any("DmlExecutionProvider" in p or p == "DmlExecutionProvider" for p in providers)


def probe_torch_cuda() -> bool:
    try:
        import importlib.util

        if importlib.util.find_spec("torch") is None:
            return False
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def probe_torch_mps() -> bool:
    try:
        import importlib.util

        if importlib.util.find_spec("torch") is None:
            return False
        import torch

        return bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    except Exception:
        return False


def build_onnx_provider_attempts() -> list[tuple[BackendName, list[Any]]]:
    """Ordered ONNX Runtime provider lists to try (CUDA -> DirectML -> CPU)."""
    attempts: list[tuple[BackendName, list[Any]]] = []
    available = set(get_onnxruntime_available_providers())
    if "CUDAExecutionProvider" in available:
        attempts.append(
            (
                BackendName.CUDA,
                [
                    (
                        "CUDAExecutionProvider",
                        {"cudnn_conv_algo_search": "HEURISTIC"},
                    )
                ],
            )
        )
    if "DmlExecutionProvider" in available:
        attempts.append((BackendName.DIRECTML, ["DmlExecutionProvider"]))
    attempts.append((BackendName.CPU, ["CPUExecutionProvider"]))
    return attempts


def select_torch_device(preferred: str = "auto") -> tuple[str, BackendName]:
    pref = (preferred or "auto").strip().lower()
    if pref == "cpu":
        return "cpu", BackendName.CPU
    if pref == "cuda":
        if probe_torch_cuda():
            return "cuda", BackendName.CUDA
        logger.warning("PyTorch CUDA requested but unavailable — using CPU")
        return "cpu", BackendName.CPU
    if pref == "mps":
        if probe_torch_mps():
            return "mps", BackendName.MPS
        logger.warning("PyTorch MPS requested but unavailable — using CPU")
        return "cpu", BackendName.CPU
    if probe_torch_cuda():
        return "cuda", BackendName.CUDA
    if probe_torch_mps():
        return "mps", BackendName.MPS
    return "cpu", BackendName.CPU


def record_backend(component: str, backend: BackendName, detail: str) -> None:
    _selections[component] = BackendSelection(component=component, backend=backend, detail=detail)
    logger.info("Local inference backend [%s]: %s (%s)", component, backend.value, detail)


def get_recorded_backends() -> dict[str, BackendSelection]:
    return dict(_selections)


def _dependency_hints() -> list[str]:
    hints: list[str] = []
    if is_windows():
        if not probe_directml_onnx():
            hints.append("AMD/Intel GPU TTS: pip install onnxruntime-directml")
        if not probe_cuda_onnx() and not probe_torch_cuda():
            hints.append("NVIDIA GPU: pip install onnxruntime-gpu (Piper) + CUDA runtime (Whisper)")
    return hints


def probe_startup_backends() -> list[str]:
    """Lightweight probe lines for startup banner (no model load)."""
    lines: list[str] = []
    whisper_pref = "auto (CUDA -> CPU)"
    if not probe_torch_cuda():
        whisper_pref += " — DirectML not supported by faster-whisper"
    lines.append(f"  STT (faster-whisper): {whisper_pref}")

    onnx_available = get_onnxruntime_available_providers()
    if onnx_available:
        preferred = []
        if probe_cuda_onnx():
            preferred.append("CUDA")
        if probe_directml_onnx():
            preferred.append("DirectML")
        preferred.append("CPU")
        lines.append(f"  ONNX (Piper TTS):     {' -> '.join(preferred)}")
    else:
        lines.append("  ONNX (Piper TTS):     CPU (onnxruntime not installed)")

    torch_backend, _ = select_torch_device("auto")
    lines.append(f"  PyTorch (NeuTTS):     {torch_backend}")

    for hint in _dependency_hints():
        lines.append(f"  [hint] {hint}")
    return lines


def format_backend_summary_for_terminal() -> str:
    """Plain-text summary for CLI banner."""
    lines = ["Local inference hardware (Hermes in-process):"]
    if _selections:
        for sel in _selections.values():
            lines.append(f"  {sel.component}: {sel.backend.value} — {sel.detail}")
    else:
        lines.extend(probe_startup_backends()[1:])  # skip duplicate header style
    return "\n".join(lines)


def log_local_inference_backends(console: Any | None = None) -> None:
    """Print selected/probed backends once at startup."""
    global _startup_summary_printed
    if _startup_summary_printed:
        return
    _startup_summary_printed = True

    lines = probe_startup_backends()
    header = "[dim]Local inference hardware (Hermes in-process):[/]"
    if console is not None:
        console.print(header)
        for line in lines:
            console.print(f"[dim]{line}[/]")
    else:
        print("Local inference hardware (Hermes in-process):")
        for line in lines:
            print(line)


def load_faster_whisper_model(model_name: str, preferred_device: str = "auto"):
    """Load faster-whisper with CUDA/auto -> CPU fallback."""
    from faster_whisper import WhisperModel

    pref = (preferred_device or "auto").strip().lower()
    if pref == "cpu":
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        record_backend("stt-whisper", BackendName.CPU, f"model={model_name}, compute=int8")
        return model

    device = "cuda" if pref == "cuda" else "auto"
    compute = "auto"
    try:
        model = WhisperModel(model_name, device=device, compute_type=compute)
        resolved_device = device
        if device == "auto":
            resolved_device = "cuda" if probe_torch_cuda() else "cpu"
        record_backend(
            "stt-whisper",
            BackendName.CUDA if resolved_device == "cuda" else BackendName.CPU,
            f"model={model_name}, device={resolved_device}, compute={compute}",
        )
        return model
    except Exception as exc:
        if pref == "cuda" and not looks_like_cuda_lib_error(exc):
            raise
        if pref not in {"auto", "cuda"}:
            raise
        logger.warning(
            "faster-whisper %s load failed (%s) — falling back to CPU (int8). "
            "Install NVIDIA CUDA runtime for GPU STT. DirectML is not supported by ctranslate2.",
            device,
            exc,
        )
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        record_backend("stt-whisper", BackendName.CPU, f"model={model_name}, compute=int8 (GPU fallback)")
        return model


def reload_faster_whisper_cpu(model_name: str):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    record_backend("stt-whisper", BackendName.CPU, f"model={model_name}, compute=int8 (runtime fallback)")
    return model


def load_piper_voice_with_fallback(
    model_path: str | Path,
    *,
    config_path: str | Path | None = None,
    espeak_data_dir: str | Path | None = None,
    download_dir: str | Path | None = None,
    prefer_cuda: bool | None = None,
):
    """Load Piper with ONNX provider chain CUDA -> DirectML -> CPU."""
    import onnxruntime

    from piper import PiperVoice
    from piper.config import PiperConfig
    from piper.phonemize_espeak import ESPEAK_DATA_DIR

    model_path = Path(model_path)
    if config_path is None:
        config_path = model_path.with_suffix(model_path.suffix + ".json")
    config_path = Path(config_path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Piper voice config not found: {config_path}")

    with config_path.open(encoding="utf-8") as config_file:
        config_dict = json.load(config_file)

    all_attempts = build_onnx_provider_attempts()
    if prefer_cuda is False:
        attempts = [a for a in all_attempts if a[0] != BackendName.CUDA]
    elif prefer_cuda is True:
        cuda_first = [a for a in all_attempts if a[0] == BackendName.CUDA]
        rest = [a for a in all_attempts if a[0] != BackendName.CUDA]
        attempts = cuda_first + rest
    else:
        attempts = all_attempts
    if not attempts:
        attempts = [(BackendName.CPU, ["CPUExecutionProvider"])]

    resolved_espeak = Path(espeak_data_dir) if espeak_data_dir else ESPEAK_DATA_DIR
    resolved_download = Path(download_dir) if download_dir else Path.cwd()

    last_exc: Exception | None = None
    for backend, providers in attempts:
        try:
            session = onnxruntime.InferenceSession(
                str(model_path),
                sess_options=onnxruntime.SessionOptions(),
                providers=providers,
            )
            active = session.get_providers()[0] if session.get_providers() else "CPUExecutionProvider"
            record_backend("piper-tts", backend, f"providers={active}")
            return PiperVoice(
                config=PiperConfig.from_dict(config_dict),
                session=session,
                espeak_data_dir=resolved_espeak,
                download_dir=resolved_download,
            )
        except Exception as exc:
            last_exc = exc
            logger.warning("Piper ONNX load failed with %s: %s", providers, exc)

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Piper load failed: no ONNX providers available")


def resolve_whisper_device_from_env(
    env_device: str | None,
    *,
    has_cuda: Callable[[], bool] | None = None,
) -> tuple[str, str]:
    """Resolve faster-whisper device/compute from env (RAG pipeline)."""
    cuda_probe = has_cuda or probe_torch_cuda
    device = (env_device or "auto").strip().lower()
    if device == "auto":
        device = "cuda" if cuda_probe() else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    backend = BackendName.CUDA if device == "cuda" else BackendName.CPU
    record_backend("rag-whisper", backend, f"device={device}, compute={compute}")
    return device, compute


def reset_hardware_backend_cache() -> None:
    """Clear cached ONNX provider list and recorded selections (tests)."""
    global _onnx_providers_cache, _startup_summary_printed
    _onnx_providers_cache = None
    _startup_summary_printed = False
    _selections.clear()
