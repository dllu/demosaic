"""A load-time repair must reject any already executed prediction evidence."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import repair_frequency_quality_identity as repair
from train_directional_bank_trial import save


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(repair, "live", lambda owner: False)
    root = tmp_path / "failed"
    archive = root / "artifacts/photo/archive"
    for name in ("predictions", "supervision"):
        (archive / name).mkdir(parents=True)
    (archive / "records.jsonl").write_text("")
    for name in ("controller.claim", "photo.claim"):
        (root / name).touch()
    (root / "photo-v1.log").write_text(
        "Fixture load traceback\nassert len(model.restoration_state_dict()) == 91\nAssertionError\n"
    )
    plan = {"root": str(root)}
    evaluation = {
        "stages": {
            "photo": {"output": str(root / "artifacts/photo")},
            "known": {"output": str(root / "artifacts/known")},
        }
    }
    save(root / "evaluation-plan-v1.json", evaluation)
    state = {
        "status": "failed-quality-evaluation-preserved-no-automatic-retry",
        "owner": {},
        "child": {"fixture": True},
        "stage": "photo",
        "completed": {},
    }
    return root, plan, state


def test_exact_empty_load_failure_is_eligible_without_neural_calls(tmp_path, monkeypatch):
    root, plan, state = fixture(tmp_path, monkeypatch)
    assert repair.zero_forward_failure(plan, state)["stages"]["photo"]["output"] == str(
        root / "artifacts/photo"
    )


@pytest.mark.parametrize(
    "evidence",
    ["journal", "prediction", "supervision", "later-stage", "wrong-failure", "live-owner"],
)
def test_any_spent_work_or_wrong_failure_rejects_repair(tmp_path, monkeypatch, evidence):
    root, plan, state = fixture(tmp_path, monkeypatch)
    archive = root / "artifacts/photo/archive"
    if evidence == "journal":
        (archive / "records.jsonl").write_text('{"fixture":"completed record"}\n')
    elif evidence in ("prediction", "supervision"):
        directory = "predictions" if evidence == "prediction" else "supervision"
        (archive / directory / "fixture.txt").write_text("Nonempty preserved fixture output")
    elif evidence == "later-stage":
        (root / "artifacts/known").mkdir()
    elif evidence == "wrong-failure":
        (root / "photo-v1.log").write_text("Unrelated failure\n")
    else:
        monkeypatch.setattr(repair, "live", lambda owner: True)
    with pytest.raises(AssertionError):
        repair.zero_forward_failure(plan, state)
