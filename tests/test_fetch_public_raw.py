import fcntl
import hashlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    "fetch_public_raw", Path(__file__).resolve().parents[1] / "scripts/fetch_public_raw.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def selection(tmp_path):
    content = b"A checksum-pinned RAW fixture, not decoded or admitted to training."
    metadata = tmp_path / "exif.txt"
    metadata.write_text("Exif.Photo.ISOSpeedRatings 100\nExif.Photo.DateTimeOriginal 2020:01:01\n")
    raw_link = (
        "<a href='https://raw.pixls.us/getfile.php/123/nice/Camera - Model.NEF'>RAW</a>"
        "<span title='sha256 Checksum'>" + hashlib.sha256(content).hexdigest() + "</span>"
    )
    meta_url = "https://raw.pixls.us/getfile.php/123/exif/file.txt"
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            {
                "data": [
                    [
                        "Make",
                        "Model",
                        "14bit",
                        40,
                        "",
                        f"<a href='{module.CC0}'>CC0</a>",
                        "2020-01-01",
                        raw_link,
                        f"<a href='{meta_url}'>EXIF</a>",
                    ]
                ]
            }
        )
    )
    survey = tmp_path / "survey.json"
    survey.write_text(
        json.dumps(
            {
                "catalog_sha256": module.checksum(catalog),
                "scouted": [
                    {
                        "make": "Make",
                        "model": "Model",
                        "mode": "14bit",
                        "license_url": module.CC0,
                        "raw_link_html": raw_link,
                        "metadata_file": str(metadata),
                        "metadata_url": meta_url,
                        "metadata_sha256": module.checksum(metadata),
                    }
                ],
            }
        )
    )
    return survey, catalog, metadata, content, tmp_path / "acquisition"


def test_verified_acquisition_archives_license_metadata_and_remains_quarantined(
    selection, monkeypatch
):
    survey, catalog, metadata, content, output = selection
    calls = []

    def urlopen(request, **kwargs):
        head = not isinstance(request, str) and request.get_method() == "HEAD"
        calls.append("HEAD" if head else "GET")
        response = io.BytesIO(b"" if head else content)
        response.headers = {"Content-Length": str(len(content))}
        return response

    monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(module.shutil, "disk_usage", lambda p: SimpleNamespace(free=2 * 1024**4))
    result = module.fetch_public_raw(survey, catalog, output)
    assert calls == ["HEAD", "GET"]
    row = result["files"][0]
    assert row["license_url"] == module.CC0 and row["sha256"] == hashlib.sha256(content).hexdigest()
    assert Path(row["metadata_path"]).read_bytes() == metadata.read_bytes()
    assert (output / "files/123.nef").read_bytes() == content
    assert "NOT a training manifest" in result["usage"]
    assert "split" not in result and "rows" not in result
    second = module.fetch_public_raw(survey, catalog, output)
    assert second == result and calls == ["HEAD", "GET"]


@pytest.mark.parametrize("change", ["license", "metadata", "catalog", "metadata-url"])
def test_changed_or_unlicensed_selection_rejected_before_network(selection, monkeypatch, change):
    survey, catalog, metadata, _, output = selection
    if change == "metadata":
        metadata.write_text("changed metadata")
    elif change == "catalog":
        catalog.write_text("{}")
    else:
        d = json.loads(survey.read_text())
        if change == "license":
            c = json.loads(catalog.read_text())
            c["data"][0][5] = "<a href='https://example.invalid/noncommercial'>NC</a>"
            catalog.write_text(json.dumps(c))
            d["catalog_sha256"] = module.checksum(catalog)
        else:
            d["scouted"][0]["metadata_url"] = "https://raw.pixls.us/getfile.php/999/exif/wrong"
        survey.write_text(json.dumps(d))

    def no_network(*args, **kwargs):
        pytest.fail("Invalid selection must fail before network I/O")

    monkeypatch.setattr(module.urllib.request, "urlopen", no_network)
    with pytest.raises(ValueError):
        module.fetch_public_raw(survey, catalog, output)
    assert not (output / "manifest.json").exists()


def test_standing_capture_metadata_cannot_enter_candidate_selection(selection):
    survey, catalog, metadata, _, _ = selection
    metadata.write_text("Exif.Photo.ISOSpeedRatings 100\nExif.Image.ImageName DSCF3880\n")
    d = json.loads(survey.read_text())
    d["scouted"][0]["metadata_sha256"] = module.checksum(metadata)
    survey.write_text(json.dumps(d))
    with pytest.raises(ValueError, match="Standing GFX"):
        module.select_candidates(survey, catalog)


def test_existing_output_owner_prevents_duplicate_acquisition(selection):
    survey, catalog, _, _, output = selection
    output.mkdir()
    with (output / ".fetch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="owns"):
            module.fetch_public_raw(survey, catalog, output)
    assert not (output / "manifest.json").exists()


@pytest.mark.parametrize("suffix", ["CR2", "CR3", "PEF", "ORF", "SRW", "NRW"])
def test_additional_camera_containers_retain_exact_license_and_checksum_guards(selection, suffix):
    survey, catalog, _, content, _ = selection
    source = json.loads(catalog.read_text())
    source["data"][0][7] = source["data"][0][7].replace("Model.NEF", "Model." + suffix)
    catalog.write_text(json.dumps(source))
    proposal = json.loads(survey.read_text())
    proposal["catalog_sha256"] = module.checksum(catalog)
    proposal["scouted"][0]["raw_link_html"] = source["data"][0][7]
    survey.write_text(json.dumps(proposal))
    record = module.select_candidates(survey, catalog)[0]
    assert record["filename"] == "123." + suffix.lower()
    assert record["publisher_checksum"]["value"] == hashlib.sha256(content).hexdigest()
    assert record["license_url"] == module.CC0
    # Accepting a container never makes it a decoded or admitted source.
    assert "split" not in record and "rows" not in record


@pytest.mark.parametrize("suffix", ["jpg", "zip", "exe"])
def test_non_raw_container_still_fails_before_acquisition(selection, suffix):
    survey, catalog, _, _, _ = selection
    source = json.loads(catalog.read_text())
    source["data"][0][7] = source["data"][0][7].replace("Model.NEF", "Model." + suffix)
    catalog.write_text(json.dumps(source))
    proposal = json.loads(survey.read_text())
    proposal["catalog_sha256"] = module.checksum(catalog)
    proposal["scouted"][0]["raw_link_html"] = source["data"][0][7]
    survey.write_text(json.dumps(proposal))
    with pytest.raises(ValueError, match="Unexpected RAW file extension"):
        module.select_candidates(survey, catalog)
