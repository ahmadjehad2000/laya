import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def home():
    return Path(os.environ.get("LAYA_COMPANION_HOME", Path.home() / ".laya-for-codex"))


@dataclass(frozen=True)
class Config:
    model: str = "multilingual"
    device: str = "auto"
    max_items: int = 32
    max_questions: int = 16
    question_batch_size: int = 4
    max_request_bytes: int = 131072
    cache_entries: int = 128
    cache_ttl_sec: int = 120
    idle_unload_sec: int = 600
    min_free_ram_gib: float = 1.0
    min_free_vram_gib: float = 2.5
    memory_reserve_gib: float = 0.75
    threads: int = 4
    verify_choice_order: bool = False

    def __post_init__(self):
        if type(self.verify_choice_order) is not bool:
            raise ValueError("verify_choice_order must be boolean")
        if self.model not in ("auto", "english", "multilingual", "typed-decisions"):
            raise ValueError("model must be auto, english, multilingual, or typed-decisions")
        if self.device not in ("auto", "cpu", "cuda", "mps"):
            raise ValueError("device must be auto, cpu, cuda, or mps")
        bounds = {"max_items": (1, 128), "max_questions": (1, 32),
                  "question_batch_size": (1, 16), "max_request_bytes": (1024, 1048576),
                  "cache_entries": (0, 1024), "cache_ttl_sec": (0, 3600),
                  "idle_unload_sec": (1, 86400), "threads": (1, 32)}
        for key, (low, high) in bounds.items():
            value = getattr(self, key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{key} must be an integer from {low} to {high}")
        for key in ("min_free_ram_gib", "min_free_vram_gib", "memory_reserve_gib"):
            value = getattr(self, key)
            if type(value) not in (int, float) or not 0.5 <= value <= 128:
                raise ValueError(f"{key} must be between 0.5 and 128")

    @classmethod
    def read(cls, root=None):
        path = (root or home()) / "config.json"
        settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        for field in ("device", "model"):
            if value := os.environ.get("LAYA_COMPANION_" + field.upper()):
                settings[field] = value
        return cls(**settings)

    def as_dict(self):
        return asdict(self)
