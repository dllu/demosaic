"""Explicit frozen-encoder identities for source-frozen experiment operators."""

import re
from collections.abc import Mapping

CONVNEXT_TINY_SHA256 = "370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd"


def sha256_identity(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Frozen backbone requires a full lowercase SHA256")
    return value


def backbone_identity(model_config, sha256):
    """Bind the architecture/revision to a separately measured parameter hash."""
    identity = {
        "model": model_config.get("dino_model"),
        "revision": model_config.get("dino_revision"),
        "sha256": sha256,
    }
    return validate_backbone_identity(identity)


def validate_backbone_identity(identity):
    if not isinstance(identity, Mapping) or set(identity) != {"model", "revision", "sha256"}:
        raise ValueError("Frozen backbone identity requires model, revision and sha256")
    name, revision = identity["model"], identity["revision"]
    if not isinstance(name, str) or not name or name != name.strip():
        raise ValueError("Frozen backbone requires an explicit model name")
    if not isinstance(revision, str) or re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise ValueError("Frozen backbone requires a pinned 40-character revision")
    return {"model": name, "revision": revision, "sha256": sha256_identity(identity["sha256"])}


def verify_backbone_identity(model_config, actual_sha256, record, *, legacy_sha256):
    """Preserve legacy shared-hash checks; explicit records also check name/revision."""
    identity = record.get("expected_backbone")
    if identity is None:
        expected_sha256 = sha256_identity(legacy_sha256)
    else:
        identity = validate_backbone_identity(identity)
        expected_sha256 = identity["sha256"]
        if (
            model_config.get("dino_model") != identity["model"]
            or model_config.get("dino_revision") != identity["revision"]
        ):
            raise ValueError("Loaded frozen backbone model/revision differs from its record")
    if sha256_identity(actual_sha256) != expected_sha256:
        raise ValueError("Loaded frozen backbone parameters differ from their SHA256")
    return expected_sha256
