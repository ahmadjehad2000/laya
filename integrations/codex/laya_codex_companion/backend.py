import gc
import os

from .checkpoints import MODELS, model_path, ready
from .validation import context_check
from .resources import memory_plan


class Backend:
    """Adapter to upstream Router and Agent, with no alternative inference runtime."""

    def __init__(self, root, config):
        os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", USE_TF="0",
                          USE_TORCH="1", TOKENIZERS_PARALLELISM="false", HF_HUB_DISABLE_TELEMETRY="1")
        import torch
        from laya import Router

        torch.set_num_threads(config.threads)
        self.torch = torch
        self.config = config
        self.root = root
        self.router = Router(models={key: str(model_path(root, key)) for key in MODELS},
                             device=config.device if config.device != "auto" else None,
                             max_loaded=1, auto_task_detection=False)
        self.fallback_reason = None

    def route(self, state, questions, model):
        decision = dict(self.router.route(state, questions, model=None if model == "auto" else model))
        decision["repo"] = MODELS[decision["model"]]["repo"]
        return decision

    def load(self, name):
        if not ready(self.root, name):
            raise FileNotFoundError(f"Checkpoint {name} is not prepared. Run laya-for-codex prepare --model {name}")
        if name not in self.router.loaded:
            # Upstream evicts AFTER loading; release first to avoid two-model memory peaks.
            self.release()
            torch = self.torch
            self.fallback_reason = None
            requested = self.config.device
            device = requested
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
            if device == "cuda":
                if not torch.cuda.is_available():
                    self.fallback_reason, device = "CUDA unavailable", "cpu"
                elif torch.cuda.mem_get_info()[0] / 2**30 < memory_plan(self.root, name, self.config)["required_cuda_vram_gib"]:
                    self.fallback_reason, device = "Insufficient free CUDA memory", "cpu"
            if device == "mps" and not torch.backends.mps.is_available():
                self.fallback_reason, device = "MPS unavailable", "cpu"
            self.router.device = device
        agent = self.router.load(name)
        if str(agent.device) != self.router.device and self.fallback_reason is None:
            self.fallback_reason = "Upstream fell back while loading the checkpoint"
        return agent

    def check(self, agent, state, questions):
        return context_check(agent, state, questions)

    def predict(self, agent, state, questions):
        before = str(agent.device)
        result = agent.predict(state, questions)
        if str(agent.device) != before:
            self.fallback_reason = "Upstream fell back during inference"
        return result

    def release(self):
        self.router.unload()
        gc.collect()
        if self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()
        if self.torch.backends.mps.is_available():
            self.torch.mps.empty_cache()
