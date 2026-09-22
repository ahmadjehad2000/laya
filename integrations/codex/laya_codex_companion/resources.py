"""Checkpoint-aware memory estimates; read only the safetensors header, never weights."""
from functools import lru_cache
import json
import math
import struct

from .checkpoints import model_path


class ResourcePressureError(MemoryError):
    def __init__(self, details):
        self.details = details
        super().__init__(
            f"Insufficient available RAM for {details['checkpoint']}: "
            f"{details['available_ram_gib']:.2f} GiB available, "
            f"{details['required_ram_gib']:.2f} GiB required by the "
            f"{'cold-load estimate' if details['cold'] else 'warm reserve'}. "
            "No prediction was produced. Release unused models/apps and retry. "
            "Check laya_status checkpoint estimates before switching models; English is not always smaller."
        )


@lru_cache(maxsize=12)
def _sizes(path, size, modified):
    # size/mtime are part of the cache key. Pinned weight integrity is checked at setup.
    with open(path, "rb") as stream:
        raw = stream.read(8)
        if len(raw) != 8:
            raise ValueError("Invalid safetensors header")
        length = struct.unpack("<Q", raw)[0]
        if not 2 <= length <= min(size - 8, 16 * 2**20):
            raise ValueError("Invalid safetensors header length")
        header = json.loads(stream.read(length))
    # Upstream constructs FP32 parameters before copying checkpoint weights on every device.
    fp32 = sum(math.prod(value["shape"]) * 4 for key, value in header.items() if key != "__metadata__")
    return size / 2**30, fp32 / 2**30


def memory_plan(root, name, config, cold=True):
    path = model_path(root, name) / "model.safetensors"
    weights = fp32 = None
    if path.is_file():
        stat = path.stat()
        weights, fp32 = _sizes(str(path), stat.st_size, stat.st_mtime_ns)
    estimate = (weights + fp32 + config.memory_reserve_gib) if weights is not None else config.min_free_ram_gib
    return {"checkpoint": name, "cold": cold, "weight_file_gib": weights,
            "fp32_parameters_gib": fp32, "reserve_gib": config.memory_reserve_gib,
            "required_ram_gib": max(config.min_free_ram_gib, estimate) if cold else max(.5, config.memory_reserve_gib),
            "required_cuda_vram_gib": max(config.min_free_vram_gib, (fp32 or 0) + config.memory_reserve_gib),
            "method": "checkpoint bytes + FP32 parameter bytes + reserve; estimate, not a peak-memory guarantee"}
