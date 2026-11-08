"""CPU-only dependency proof for V178 GPU work; absence alone is not success."""

import hashlib
import json
from pathlib import Path

import psutil


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def owner_live(owner):
    """Transient/permission errors propagate, never turning an owner terminal."""
    try:
        process = psutil.Process(owner["pid"])
        return process.create_time() == owner["created"] and process.status() not in (
            psutil.STATUS_ZOMBIE,
            psutil.STATUS_DEAD,
        )
    except psutil.NoSuchProcess:
        return False


def dependency_readiness(root, *, is_live=owner_live):
    """Require terminal train/review/watch owners and the completed pipeline."""
    root = Path(root)
    for name in [
        "train-failure-v1.json",
        "review-failure-v1.json",
        "completion-watch-failure-v1.json",
    ]:
        if (root / name).exists():
            raise RuntimeError(f"Preserved dependency failure requires inspection: {root / name}")
    bindings, owners = [], {}
    phases = [
        ("train", "train-result-v1.json"),
        ("review", "scores-v1.json"),
        ("completion-watch", "completion-watch-result-v1.json"),
    ]
    for phase, result_name in phases:
        launch_path = root / f"{phase}-launch-v1.json"
        if not launch_path.exists():
            return {"ready": False, "reason": f"waiting-for-{phase}-launch"}
        launch = read(launch_path)
        owner = launch["owner"]
        owners[phase] = owner
        if is_live(owner):
            return {"ready": False, "reason": f"waiting-for-{phase}-owner", "owner": owner}
        result_path = root / result_name
        if not result_path.exists():
            return {
                "ready": False,
                "reason": f"waiting-for-{phase}-completed-result",
                "owner": owner,
            }
        result = read(result_path)
        if result.get("owner") != owner or not result.get("status", "").startswith("completed"):
            raise RuntimeError(f"Dependency result does not prove {phase} success: {result_path}")
        bindings.extend([ref(launch_path), ref(result_path)])
    status_path = root / "completion-watch-status-v1.json"
    status = read(status_path)
    if (
        status["owner"] != owners["completion-watch"]
        or status["status"] != "ready-for-actual-native-viewing"
    ):
        raise RuntimeError("Completion watcher did not reach its final native-viewing state")
    for name in [
        "training-audit-v1.json",
        "quality-audit-v1.json",
        "offset-audit-v1.json",
        "paired-comparisons-v1.json",
        "figures-v1.json",
    ]:
        path = root / name
        if not path.exists():
            raise RuntimeError(f"Completed dependency is missing required output: {path}")
        value = read(path)
        if not value.get("status", "").startswith(("pass", "completed", "rendered")):
            raise RuntimeError(f"Dependency output lacks completed status: {path}")
        bindings.append(ref(path))
    bindings.append(ref(status_path))
    return {
        "ready": True,
        "reason": "all-V175-owners-terminal-completed-audits-review-render",
        "owners": owners,
        "bindings": bindings,
        "scope": "Ready for separate GPU admission;V175 human viewing/report/publication may remain.",
    }
