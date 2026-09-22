import hashlib
import json
import threading
import time
from collections import OrderedDict
from copy import deepcopy

import psutil

from . import __version__
from .checkpoints import MODELS, ready
from .config import Config, home
from .validation import bounded_json, questions_check, request_check


class Runtime:
    def __init__(self, root=None, config=None, backend_factory=None):
        self.root = root or home()
        self.config = config or Config.read(self.root)
        self.factory = backend_factory
        self.backend = None
        self.lock = threading.RLock()
        self.cache = OrderedDict()
        self.calls = self.hits = self.errors = 0
        self.last_use = time.monotonic()
        self.device = None
        self.stop = threading.Event()
        self.reaper = threading.Thread(target=self._idle, daemon=True)
        self.reaper.start()

    def _idle(self):
        while not self.stop.wait(min(10, self.config.idle_unload_sec)):
            if self.lock.acquire(blocking=False):
                try:
                    if self.backend and time.monotonic() - self.last_use >= self.config.idle_unload_sec:
                        self._release()
                finally:
                    self.lock.release()

    def _release(self):
        if self.backend:
            self.backend.release()
        self.cache.clear()
        self.device = None

    def close(self):
        self.stop.set()
        self.reaper.join(timeout=2)
        with self.lock:
            self._release()

    def status(self):
        if not self.lock.acquire(blocking=False):
            return {"version": __version__, "busy": True}
        try:
            return {"version": __version__, "runtime": "upstream-laya-pytorch", "busy": False,
                    "configuration": self.config.as_dict(), "device": self.device,
                    "loaded": list(self.backend.router.loaded) if self.backend else [],
                    "checkpoints": {k: {**v, "prepared": ready(self.root, k)} for k, v in MODELS.items()},
                    "ram_available_gib": round(psutil.virtual_memory().available / 2**30, 2),
                    "process_rss_mib": round(psutil.Process().memory_info().rss / 2**20, 1),
                    "calls": self.calls, "cache_hits": self.hits, "errors": self.errors,
                    "cache_entries": len(self.cache),
                    "scope": "Advisory decisions; Codex retains reasoning and execution permissions"}
        finally:
            self.lock.release()

    def predict(self, state, questions, use_cache=True, model=None):
        raw = request_check(state, questions, self.config)
        selected = model or self.config.model
        if selected not in (*MODELS, "auto"):
            raise ValueError("Unknown model; choose auto, english, multilingual, or typed-decisions")
        with self.lock:
            start = time.perf_counter()
            self.calls += 1
            try:
                return self._predict(state, questions, raw, selected, use_cache, start)
            except Exception:
                self.errors += 1
                raise
            finally:
                self.last_use = time.monotonic()

    def _predict(self, state, questions, raw, selected, use_cache, start):
        if self.backend is None:
            if self.factory is None:
                from .backend import Backend
                self.factory = Backend
            self.backend = self.factory(self.root, self.config)
        route = self.backend.route(state, questions, selected)
        name = route["model"]
        key = hashlib.sha256((raw + name + MODELS[name]["revision"]).encode()).hexdigest()
        now = time.monotonic()
        for old in list(self.cache):
            if now - self.cache[old][0] >= self.config.cache_ttl_sec:
                self.cache.pop(old)
        if use_cache and key in self.cache:
            self.hits += 1
            self.cache.move_to_end(key)
            result = deepcopy(self.cache[key][1])
            result["routing"] = route
            result["original_runtime"] = result.pop("runtime")
            result["runtime"] = {"cache_hit": True, "inference_ms": 0, "load_ms": 0,
                                 "elapsed_ms": round((time.perf_counter() - start) * 1000, 2)}
            return result
        cold = name not in self.backend.router.loaded
        floor = self.config.min_free_ram_gib if cold else 0.5
        if psutil.virtual_memory().available / 2**30 < floor:
            self._release()
            raise MemoryError(f"Need at least {floor} GiB available RAM; model released")
        loading = time.perf_counter()
        agent = self.backend.load(name)
        load_ms = (time.perf_counter() - loading) * 1000 if cold else 0
        context = self.backend.check(agent, state, questions)
        inference = time.perf_counter()
        answers, tokens = {}, 0
        entries = list(questions.items())
        try:
            for i in range(0, len(entries), self.config.question_batch_size):
                part = self.backend.predict(agent, state, dict(entries[i:i + self.config.question_batch_size]))
                answers.update(part["answers"])
                tokens += part["usage"]["input_tokens"]
        except (MemoryError, RuntimeError):
            agent = None
            self._release()
            raise
        inference_ms = (time.perf_counter() - inference) * 1000
        self.device = str(agent.device)
        result = {"model": "laya-rl-agent", "answers": answers,
                  "usage": {"input_tokens": tokens, "output_tokens": 0}, "routing": route,
                  "checkpoint": {"variant": name, **MODELS[name]}, "context_tokens": context,
                  "runtime": {"backend": "pytorch", "device": self.device,
                              "fallback_reason": self.backend.fallback_reason,
                              "cache_hit": False, "load_ms": round(load_ms, 2),
                              "inference_ms": round(inference_ms, 2),
                              "elapsed_ms": round((time.perf_counter() - start) * 1000, 2)}}
        json.dumps(result, allow_nan=False)
        if use_cache and self.config.cache_entries and self.config.cache_ttl_sec:
            self.cache[key] = (time.monotonic(), deepcopy(result))
            while len(self.cache) > self.config.cache_entries:
                self.cache.popitem(last=False)
        return result

    def predict_batch(self, items, questions, use_cache=True, model=None):
        questions_check(questions, self.config)
        if not isinstance(items, list) or not 1 <= len(items) <= self.config.max_items:
            raise ValueError(f"Supply 1–{self.config.max_items} items")
        bounded_json([items, questions], self.config.max_request_bytes)
        ids = []
        for item in items:
            if not isinstance(item, dict) or set(item) != {"id", "state"}:
                raise ValueError("Each item must contain exactly id and state")
            if not isinstance(item["id"], str) or not 1 <= len(item["id"]) <= 120:
                raise ValueError("Item IDs must be 1–120 characters")
            ids.append(item["id"])
        if len(set(ids)) != len(ids):
            raise ValueError("Item IDs must be unique")
        results = []
        # Independent item contexts; not heterogeneous tensor batching.
        for item in items:
            try:
                result = self.predict(item["state"], questions, use_cache, model)
                results.append({"id": item["id"], "result": result})
            except (ValueError, FileNotFoundError, MemoryError, RuntimeError) as exc:
                results.append({"id": item["id"], "error": {"type": type(exc).__name__, "message": str(exc)}})
        return {"items": results, "succeeded": sum("result" in r for r in results),
                "failed": sum("error" in r for r in results)}

    def release(self):
        with self.lock:
            self._release()
            return {"released": True, "cache_cleared": True}

    def benchmark(self, iterations=3):
        if type(iterations) is not int or not 3 <= iterations <= 10:
            raise ValueError("iterations must be from 3 to 10")
        state = "The customer was charged twice and requests a refund."
        questions = {"team": {"type": "choice", "instructions": "Which team handles this?",
                              "criteria": {"billing": "payments and refunds", "technical": "software errors"}}}
        runs = [self.predict(state, questions, False) for _ in range(iterations)]
        return {"iterations": iterations, "runs": [r["runtime"] for r in runs],
                "labels": [r["answers"]["team"]["choice"] for r in runs],
                "scope": "Synthetic diagnostic only; excludes Codex and MCP overhead; no task accuracy claim"}
