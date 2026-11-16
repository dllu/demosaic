"""Content-addressed inputs, immutable publications and source snapshots."""

import ast
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


def read_json(path):
    return json.loads(Path(path).read_text())


def reference(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def checked(binding):
    """Check the file identity; additional descriptive metadata is permitted."""
    actual = reference(binding["path"])
    if actual["sha256"] != binding["sha256"]:
        raise ValueError(f"Artifact digest mismatch: {binding['path']}")
    return Path(actual["path"])


def write_json(path, value, *, replace=False):
    """Atomically publish complete JSON; receipts are exclusive by default."""
    data = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix="." + path.name, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            temporary.replace(path)
        else:
            os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verify_plan(plan):
    for binding in plan["inputs"]:
        checked(binding)
    for path, digest in plan["frozen_files"].items():
        checked({"path": path, "sha256": digest})


def freeze_sources(repository, root, entries=()):
    """Copy package code and the static local import closure of legacy scripts.

    Whole-package snapshots include lazy imports and compatibility modules.
    Only code is copied; data, original photographs and caches are excluded.
    """
    repository, root = Path(repository), Path(root)
    work = root / "work"
    shutil.copytree(
        repository / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    pending, copied = list(entries), set()
    while pending:
        name = pending.pop()
        if name in copied:
            continue
        if Path(name).name != name or not name.endswith(".py"):
            raise ValueError("Snapshot entries must be Python filenames in scripts/")
        source = repository / "scripts" / name
        target = work / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.add(name)
        for node in ast.walk(ast.parse(source.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names = [node.module]
            for imported in names:
                candidate = imported.split(".")[0] + ".py"
                if (repository / "scripts" / candidate).is_file():
                    pending.append(candidate)
    return work, {str(p.absolute()): reference(p)["sha256"] for p in work.rglob("*.py")}
