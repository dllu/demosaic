import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from demosaic.paired import TRAINING_SCENES, select_pairs
from demosaic.paired_training import PairedDataset

spec = importlib.util.spec_from_file_location(
    "fetch_paired_extension",
    Path(__file__).resolve().parents[1] / "scripts/fetch_paired_extension.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def inputs(names=("new_a", "new_b")):
    dataset, files = {"Bayer": {}}, []
    for scene in names:
        clean, noisy = [], []
        for role, iso in [("clean", 100), ("clean", 200), ("noisy", 400),
                          ("noisy", 1600), ("noisy", 6400), ("noisy", 25600)]:
            digest = hashlib.sha1(f"{scene}:{iso}".encode()).hexdigest()
            filename = f"Bayer_{scene}_{'GT_' if role == 'clean' else ''}ISO{iso}_sha1={digest}.arw"
            item = {"filename": filename, "sha1": digest}
            (clean if role == "clean" else noisy).append(item)
            files.append({"restricted": False, "dataFile": {
                "filename": filename, "id": len(files) + 1, "filesize": 100,
                "checksum": {"type": "MD5", "value": "0" * 32},
            }})
        dataset["Bayer"][scene] = {"clean_images": clean, "noisy_images": noisy,
                                   "test_reserve": False, "unknown_sensor": False}
    version = {"license": {"rightsIdentifier": "CC-BY-SA-4.0"}, "files": files,
               "versionNumber": 1, "versionMinorNumber": 0}
    protected = {"protected": [{"scene": "heldout", "source": {"sha1": "f" * 40}}]}
    existing = {"split": "train", "selection": [
        {"scene": name, "clean": [{"sha1": hashlib.sha1(name.encode()).hexdigest()}], "noisy": []}
        for name in TRAINING_SCENES
    ]}
    return dataset, version, "", protected, existing


def test_metadata_selection_is_deterministic_quarantined_and_does_not_relax_train_guard():
    args = inputs(("new_b", "new_a"))
    before = copy.deepcopy(args)
    plan = module.plan_extension(*args)
    assert args == before
    assert [p["scene"] for p in plan["selection"]] == ["new_a", "new_b"]
    assert plan["files"] == 8 and plan["bytes"] == 800
    assert plan["split"] == "quarantine"
    for scene in plan["selection"]:
        assert scene["split"] == "quarantine"
        assert [f["iso_label"] for f in scene["noisy"]] == [1600, 6400]
    with pytest.raises(ValueError, match="fixed training selection"):
        select_pairs(args[0], args[1]["files"], "train", scenes=["new_a"])


def test_protected_families_reserve_unknown_and_scene_permissions_are_excluded():
    names = ["new_a", "heldout", "2pilesofplates", "MuseeL-new", "LucieB_new",
             "7D-99", "D60-99", "boardgames_bot", "reserved", "unknown", "research"]
    args = list(inputs(names))
    args[0]["Bayer"]["reserved"]["test_reserve"] = True
    args[0]["Bayer"]["unknown"]["unknown_sensor"] = True
    args[2] = "research: Copyright, fair-use / research purpose only\n"
    plan = module.plan_extension(*args)
    assert [p["scene"] for p in plan["selection"]] == ["new_a"]
    assert len(plan["excluded"]) == len(names) - 1


def test_source_aliases_and_test_filename_are_rejected():
    args = inputs(("new_a", "alias", "test_prefix"))
    args[0]["Bayer"]["alias"]["clean_images"][0]["sha1"] = "f" * 40
    args[0]["Bayer"]["test_prefix"]["clean_images"].append({"filename": "Bayer_TEST_old.xmp"})
    plan = module.plan_extension(*args)
    assert [p["scene"] for p in plan["selection"]] == ["new_a"]


def test_restricted_files_and_unreviewed_licenses_are_not_selected():
    args = inputs()
    args[1]["files"][0]["restricted"] = True
    assert [p["scene"] for p in module.plan_extension(*args)["selection"]] == ["new_b"]
    args[1]["license"]["rightsIdentifier"] = "CC-BY-NC-4.0"
    with pytest.raises(ValueError, match="commercially"):
        module.plan_extension(*args)


def test_cc0_scene_override_retains_credit():
    args = list(inputs())
    args[2] = "new_a: CC0, by Example Photographer\n"
    plan = module.plan_extension(*args)
    permission = plan["selection"][0]["permission"]
    assert permission["license"] == "CC0-1.0"
    assert permission["publisher_scene_text"] == "CC0, by Example Photographer"
    assert plan["selection"][1]["permission"]["license"] == "CC-BY-SA-4.0"


@pytest.mark.parametrize("bad", ["protected", "train"])
def test_incomplete_protection_or_existing_split_rejected(bad):
    args = inputs()
    if bad == "protected":
        args[3]["protected"] = []
    else:
        args[4]["selection"].pop()
    with pytest.raises(ValueError):
        module.plan_extension(*args)


def test_quarantine_manifest_cannot_be_loaded_as_training(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"split": "quarantine", "cases": []}))
    with pytest.raises(ValueError, match="separate train"):
        PairedDataset(path)


def test_ambiguous_permissions_are_rejected():
    with pytest.raises(ValueError, match="Ambiguous"):
        module.permissions_by_scene("scene: CC0, by A\nscene: CC0, by B")
