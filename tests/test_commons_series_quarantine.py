import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


def script():
    path = Path("scripts/quarantine_commons_series.py")
    spec = importlib.util.spec_from_file_location("series_quarantine", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path):
    rule = {
        "id": "reviewed",
        "kind": "capture_series",
        "title_prefixes": ["File:Événement 2020 "],
        "query_seed_ids": ["q"],
        "reviewed_training_seed_ids": ["related"],
    }
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"format_version": 1, "rules": [rule]}))
    paths = []
    for factor in (8, 4):
        rows = []
        for identity, title, split in [
            ("q", "File:Événement 2020 query.jpg", "val"),
            ("related", "File:E\u0301VE\u0301NEMENT 2020 other.jpg", "train"),
            ("keep", "File:Événement 2021 different.jpg", "train"),
            ("test", "File:Événement 2020 untouched.jpg", "test"),
        ]:
            rows.append(
                {
                    "id": identity,
                    "title": title,
                    "split": split,
                    "bin_factor": factor,
                    "cache": str(tmp_path / f"{identity}-{factor}.npy"),
                    "cache_sha256": "f" * 64,
                    "shape": [2048 // factor, 2048 // factor, 3],
                    "dtype": "uint16",
                    "color_space": "linear-sRGB",
                    "attribution": "Keep all original fields",
                }
            )
        if factor == 8:
            rows.append(
                {"id": "reserved", "title": "File:Événement 2020 reserved.jpg", "split": "reserved"}
            )
        path = tmp_path / f"input{factor}.jsonl"
        # Preserve real literal differences and a final line without a newline.
        path.write_bytes(
            b"\r\n".join(json.dumps(r, ensure_ascii=False, indent=None).encode() for r in rows)
        )
        paths.append(path)
    return paths, policy


def test_unicode_series_removal_preserves_every_retained_byte_and_input(tmp_path):
    paths, policy = fixture(tmp_path)
    before = [p.read_bytes() for p in paths]
    out = tmp_path / "frozen"
    result = script().quarantine(*paths, policy, out)
    assert result["quarantined_training_sources"] == 1
    for factor, payload in zip((8, 4), before, strict=True):
        lines = payload.splitlines(keepends=True)
        expected = b"".join(line for line in lines if json.loads(line)["id"] != "related")
        assert (out / f"manifest{factor}.jsonl").read_bytes() == expected
        assert (out / f"quarantined{factor}.jsonl").read_bytes() == b"".join(
            line for line in lines if json.loads(line)["id"] == "related"
        )
    assert before == [p.read_bytes() for p in paths]
    assert result["inputs"]["bin8"]["sha256"] == hashlib.sha256(before[0]).hexdigest()
    with pytest.raises(ValueError, match="already exists"):
        script().quarantine(*paths, policy, out)


@pytest.mark.parametrize(
    "problem",
    [
        "duplicate",
        "different_train",
        "different_val",
        "relative_cache",
        "bad_binning",
        "missing_seed",
    ],
)
def test_invalid_coupling_or_relocation_rejected_before_output(tmp_path, problem):
    paths, policy = fixture(tmp_path)
    rows = [json.loads(s) for s in paths[1].read_text().splitlines()]
    if problem == "duplicate":
        rows.append(dict(rows[1]))
    elif problem == "different_train":
        rows[1]["id"] = "different"
    elif problem == "different_val":
        rows[0]["id"] = "different"
    elif problem == "relative_cache":
        rows[1]["cache"] = "relative.npy"
    elif problem == "bad_binning":
        rows[1]["bin_factor"] = 8
    else:
        rows[0]["title"] = "File:Unrelated validation.jpg"
    paths[1].write_text("".join(json.dumps(r) + "\n" for r in rows))
    out = tmp_path / "bad"
    with pytest.raises(ValueError):
        script().quarantine(*paths, policy, out)
    assert not out.exists()


def test_empty_prefix_rejected_and_different_named_site_retained(tmp_path):
    module = script()
    paths, policy = fixture(tmp_path)
    value = json.loads(policy.read_text())
    value["rules"][0]["title_prefixes"] = ["File:"]
    policy.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="nonempty"):
        module.quarantine(*paths, policy, tmp_path / "bad")
    rules = [{"id": "site", "title_prefixes": ["File:Manchester Piccadilly station MMB "]}]
    assert (
        module.matching_rules("File:Birmingham International railway station MMB 03.jpg", rules)
        == []
    )
