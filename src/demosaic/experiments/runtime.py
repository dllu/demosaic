"""Explicit process ownership and execution policies, independent of any trial."""

import fcntl
import os
import random
import shutil
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

import psutil

from .artifacts import write_json


def owner_identity():
    return {"pid": os.getpid(), "created": psutil.Process().create_time()}


def owner_live(owner):
    try:
        process = psutil.Process(owner["pid"])
        return process.create_time() == owner["created"] and process.status() not in (
            psutil.STATUS_ZOMBIE,
            psutil.STATUS_DEAD,
        )
    except psutil.NoSuchProcess:
        return False


@contextmanager
def exclusive_run(root):
    """OS lock releases after crashes; stale PID files cannot block recovery."""
    root = Path(root)
    with (root / ".worker.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError(f"An experiment worker already owns {root}") from error
        try:
            write_json(root / "owner.json", owner_identity(), replace=True)
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


@dataclass(frozen=True)
class RuntimePolicy:
    device: str = "cuda"
    seed: int = 20001
    threads: int = 2
    deterministic: bool = True
    cuda_quota_gib: float = 24
    minimum_ram_gib: float = 32
    minimum_disk_gib: float = 40

    def __post_init__(self):
        import math

        if self.device not in ("cpu", "cuda") or type(self.seed) is not int:
            raise ValueError("Choose cpu/cuda and an integer seed")
        if type(self.threads) is not int or self.threads < 1:
            raise ValueError("threads must be positive")
        if type(self.deterministic) is not bool:
            raise ValueError("deterministic must be a boolean")
        for value in (self.cuda_quota_gib, self.minimum_ram_gib, self.minimum_disk_gib):
            if not math.isfinite(value) or value < 0:
                raise ValueError("Resource limits must be finite and nonnegative")
        if self.device == "cuda" and self.cuda_quota_gib == 0:
            raise ValueError("CUDA memory quota must be positive")

    def resources(self, root):
        available = psutil.virtual_memory().available / 2**30
        disk = shutil.disk_usage(root).free / 2**30
        if available < self.minimum_ram_gib or disk < self.minimum_disk_gib:
            raise RuntimeError(
                f"Resource reserve unavailable: RAM={available:.2f}, disk={disk:.2f} GiB"
            )

    def apply(self):
        import numpy as np
        import torch

        torch.set_num_threads(self.threads)
        random.seed(self.seed)
        np.random.seed(self.seed % 2**32)
        torch.manual_seed(self.seed)
        torch.set_float32_matmul_precision("highest")
        torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = self.deterministic
        torch.use_deterministic_algorithms(self.deterministic, warn_only=True)
        if self.device == "cuda":
            os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
            properties = torch.cuda.get_device_properties(0)
            fraction = self.cuda_quota_gib * 2**30 / properties.total_memory
            if fraction > 1:
                raise ValueError("CUDA quota exceeds device memory")
            torch.cuda.set_per_process_memory_fraction(fraction)

    def to_dict(self):
        return asdict(self)
