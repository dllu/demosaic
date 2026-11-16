"""Resolve checkout write roots consistently in live and frozen package trees."""

from pathlib import Path


def repository_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src/demosaic").is_dir():
            return parent
    raise ValueError("This operation requires a repository checkout")


def writable_output(path):
    path = Path(path).expanduser().resolve()
    roots = (repository_root(), Path("/mnt/external"))
    if not any(path.is_relative_to(root) for root in roots):
        raise ValueError(f"Output must be inside {roots[0]} or /mnt/external: {path}")
    if path.is_relative_to(Path("/mnt/external/qi")):
        raise ValueError("The original Commons corpus is read-only")
    return path
