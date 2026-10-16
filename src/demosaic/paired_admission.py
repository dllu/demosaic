"""Exact reviewed paired-case admission; quarantine is never admitted implicitly."""

import hashlib
import json
from pathlib import Path

from .paired import DEVELOPMENT_SCENES, TRAINING_SCENES

SOURCE_FAMILY = "rawnind-reviewed-paired-extension"
# Populate only after actual identity/content/registration review. A locally
# self-signed receipt or a changed quarantine split cannot add an entry here.
REVIEWED_ADMISSIONS = frozenset(
    {
        # 51 new publisher scene IDs, reviewed in docs/paired-extension-quarantine.md.
        "5609f2bcf17fa165828120dd25452a236a7631b89bab632fb18037161203b70e",
    }
)


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
            or case.get("source_permission", {}).get("license") not in {"CC0-1.0", "CC-BY-SA-4.0"}
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
        group = case.get("scene_group", case["scene"])
        if not isinstance(group, str) or not group or group in protected:
            raise ValueError("Invalid/protected reviewed paired scene group")
        for crop in case["crops"]:
            if not Path(crop["path"]).is_absolute() or not _sha256(crop.get("sha256")):
                raise ValueError("Reviewed paired crops require absolute paths and exact hashes")
        approved[key] = case
    if not approved:
        raise ValueError("Reviewed paired admission has no cases")
    return approved


def extend_paired_training(base_manifest, admission_path, output):
    """Build a separate reviewed extension while preserving all legacy cases."""
    from .paired_training import PairedDataset
    from .safety import writable_path

    base_manifest, admission_path = Path(base_manifest).resolve(), Path(admission_path).resolve()
    base_bytes, admission_bytes = base_manifest.read_bytes(), admission_path.read_bytes()
    base, payload = json.loads(base_bytes), json.loads(admission_bytes)
    if base.get("paired_extension_admission") is not None or base.get("split") != "train":
        raise ValueError("Choose the original train32 manifest, not an extension/quarantine")
    if {case["scene"] for case in base["cases"]} != set(TRAINING_SCENES):
        raise ValueError("Expected the complete fixed train32 selection")
    if base["dataset_license"].get("rightsIdentifier") != "CC-BY-SA-4.0":
        raise ValueError("Expected the reviewed RawNIND dataset license")
    PairedDataset(base_manifest, patch_size=32)
    envelope = {"payload": payload, "sha256": payload_digest(payload)}
    approved = approved_extension_cases({"paired_extension_admission": envelope})

    def source_hashes(cases):
        return {case["noisy"]["sha256"] for case in cases} | {
            ref["sha256"] for case in cases for ref in case["references"]
        }

    if source_hashes(base["cases"]) & source_hashes(approved.values()):
        raise ValueError("Reviewed paired source overlaps an existing train32 capture")
    cases = []
    for case in base["cases"]:
        cases.append(
            {
                **case,
                "crops": [
                    {**crop, "path": str((base_manifest.parent / crop["path"]).resolve())}
                    for crop in case["crops"]
                ],
            }
        )
    normalized_base = json.loads(json.dumps(cases))
    cases.extend(approved.values())
    result = {
        "format_version": 2,
        "split": "train",
        "cases": cases,
        "dataset_license": base["dataset_license"],
        "attribution": base["attribution"],
        "paired_extension_admission": envelope,
        "recipe": {
            "kind": "reviewed-paired-extension-v1",
            "base_manifest": str(base_manifest),
            "base_manifest_sha256": hashlib.sha256(base_bytes).hexdigest(),
            "admission_path": str(admission_path),
            "admission_file_sha256": hashlib.sha256(admission_bytes).hexdigest(),
            "admission_canonical_sha256": envelope["sha256"],
            "groups": "Original train32 scenes plus exact reviewed group aliases; repeated views/exposures share group weight",
        },
        "notes": [
            "Separate opt-in dataset; base/quarantine/source/crop bytes are unchanged.",
            "Measured clean CFA retains noise; independently calibrated AHD RGB is auxiliary, not exact GT.",
        ],
    }
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    path = output / "manifest.json"
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    dataset = PairedDataset(path, patch_size=32)
    assert json.loads(path.read_text())["cases"][: len(normalized_base)] == normalized_base
    assert (
        base_manifest.read_bytes() == base_bytes and admission_path.read_bytes() == admission_bytes
    )
    archive = output / "source"
    archive.mkdir()
    (archive / "base-manifest.json").write_bytes(base_bytes)
    (archive / "admission.json").write_bytes(admission_bytes)
    sources = {}
    for source in Path(__file__).parent.glob("*.py"):
        content = source.read_bytes()
        (archive / source.name).write_bytes(content)
        sources[source.name] = hashlib.sha256(content).hexdigest()
    receipt = {
        "manifest": str(path),
        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "base_cases_preserved": len(normalized_base),
        "reviewed_new_cases": len(approved),
        "publisher_scene_ids": len({case["scene"] for case in cases}),
        "sampling_groups": len(dataset),
        "crops": sum(len(case["crops"]) for case in cases),
        "admission_canonical_sha256": envelope["sha256"],
        "source_files": sources,
        "base_and_admission_bytes_unchanged": True,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
