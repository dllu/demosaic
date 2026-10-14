"""Enforce the workspace's authorized write locations."""

from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]


def writable_path(path) -> Path:
    path = Path(path).expanduser().resolve()
    if not any(
        path == root or root in path.parents for root in (REPOSITORY, Path("/mnt/external"))
    ):
        raise ValueError(f"Output must be inside {REPOSITORY} or /mnt/external: {path}")
    if path == Path("/mnt/external/qi") or Path("/mnt/external/qi") in path.parents:
        raise ValueError("The original Commons corpus is read-only for this project")
    return path
