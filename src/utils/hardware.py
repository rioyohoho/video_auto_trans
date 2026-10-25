from functools import lru_cache
import os
import subprocess


def get_torch_backend() -> tuple[str, str]:
    try:
        import torch

        if torch.cuda.is_available():
            backend = "rocm" if getattr(torch.version, "hip", None) else "cuda"
            return backend, torch.cuda.get_device_name(0)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps", "Apple Metal"
    except Exception:
        pass

    try:
        import torch_directml

        if torch_directml.is_available():
            try:
                name = torch_directml.device_name(0)
            except Exception:
                name = "DirectML device"
            return "directml", name
    except Exception:
        pass

    return "cpu", "CPU"


def get_gpu_backend() -> tuple[str, str]:
    try:
        import torch

        if torch.cuda.is_available():
            backend = "rocm" if getattr(torch.version, "hip", None) else "cuda"
            return backend, torch.cuda.get_device_name(0)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps", "Apple Metal"
    except Exception:
        pass

    try:
        import torch_directml

        if torch_directml.is_available():
            try:
                name = torch_directml.device_name(0)
            except Exception:
                name = "DirectML device"
            return "directml", name
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return "cuda", result.stdout.splitlines()[0].strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ';'",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=8,
            )
            names = [name.strip() for name in result.stdout.split(";") if name.strip()]
            for name in names:
                if any(vendor in name.lower() for vendor in ("amd", "radeon")):
                    return "amd", name
        except (OSError, subprocess.TimeoutExpired):
            pass

    return "cpu", "CPU"


def is_directml_available() -> bool:
    try:
        import onnxruntime
        import torch_directml

        return (
            "DmlExecutionProvider" in onnxruntime.get_available_providers()
            and torch_directml.is_available()
        )
    except Exception:
        return False


def get_ctranslate2_runtime() -> tuple[str, str]:
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            supported = ctranslate2.get_supported_compute_types("cuda")
            for compute_type in ("float16", "bfloat16", "int8_float16", "float32"):
                if compute_type in supported:
                    return "cuda", compute_type
    except Exception:
        pass

    return "cpu", "int8"


@lru_cache(maxsize=4)
def get_ffmpeg_encoders(ffmpeg_bin: str = "ffmpeg") -> frozenset[str]:
    try:
        result = subprocess.run(
            [ffmpeg_bin, "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return frozenset()

    return frozenset(
        fields[1]
        for line in result.stdout.splitlines()
        if len(fields := line.split()) > 1 and "V" in fields[0]
    )