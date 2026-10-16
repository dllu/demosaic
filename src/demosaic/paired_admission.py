"""Exact reviewed paired-case admission; quarantine is never admitted implicitly."""

import hashlib
import json
from pathlib import Path

from .paired import DEVELOPMENT_SCENES, TRAINING_SCENES

SOURCE_FAMILY = "rawnind-reviewed-paired-extension"
# Populate only after actual identity/content/registration review. A locally
# self-signed receipt or a changed quarantine split cannot add an entry here.
REVIEWED_ADMISSIONS = frozenset()


def case_key(case):
    return case["scene"], case.get("noisy", {}).get("sha256")


def payload_digest(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _sha256(value):
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def approved_extension_cases(data):
    admission = data.get("paired_extension_admission")
    if admission is None:
        return {}
    payload = admission["payload"]
    digest = payload_digest(payload)
    if digest != admission.get("sha256") or digest not in REVIEWED_ADMISSIONS:
        raise ValueError("Paired extension admission is not an exact pinned review")
    if (
        payload.get("format_version") != 1
        or payload.get("source_family") != SOURCE_FAMILY
        or payload.get("scope") != "reviewed-training-only"
    ):
        raise ValueError("Unsupported paired extension admission")
    evidence = payload["evidence"]
    for name in ["acquisition_manifest", "screen_summary", "prepared_manifest", "manual_review"]:
        if not _sha256(evidence.get(name + "_sha256")):
            raise ValueError("Paired review evidence requires exact source hashes")
    protected = payload.get("protected_scene_names")
    if (
        not protected
        or not all(isinstance(name, str) and name for name in protected)
        or not set(DEVELOPMENT_SCENES) <= set(protected)
    ):
        raise ValueError("Paired admission must preserve protected scene identities")
    approved = {}
    for case in payload["cases"]:
        key = case_key(case)
        camera = "".join(
            c for c in case.get("metadata", {}).get("camera", "") if c.isalnum()
        ).upper()
        if (
            case.get("paired_source_family") != SOURCE_FAMILY
            or case["scene"] in protected
            or case["scene"] in TRAINING_SCENES
            or case["scene"].startswith(("MuseeL-", "LucieB_", "7D-", "D60-", "boardgames_"))
            or case.get("unknown_sensor")
            or not camera
            or camera == "UNKNOWN"
            or "EOSM100" in camera
            or camera.endswith("GH1")
            or not _sha256(key[1])
            or not case.get("references")
            or any(not _sha256(r.get("sha256")) for r in case["references"])
            or not case.get("crops")
            or key in approved
        ):
            raise ValueError("Invalid/protected/duplicate reviewed paired case")
        for crop in case["crops"]:
            if not Path(crop["path"]).is_absolute() or not _sha256(crop.get("sha256")):
                raise ValueError("Reviewed paired crops require absolute paths and exact hashes")
        approved[key] = case
    if not approved:
        raise ValueError("Reviewed paired admission has no cases")
    return approved
