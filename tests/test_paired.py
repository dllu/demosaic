import hashlib
import io
import urllib.error

import pytest

from demosaic import paired


def descriptor(filename, payload=b"raw sensor bytes"):
    return {
        "filename": filename,
        "bytes": len(payload),
        "publisher_checksum": {"type": "MD5", "value": hashlib.md5(payload).hexdigest()},
        "sha1": hashlib.sha1(payload).hexdigest(),
        "url": paired.DATA_URL + "1",
    }


def fixture_catalog(scene="development", reserved=False):
    clean = [{"filename": f"Bayer_{scene}_GT_ISO100_sha1={'0' * 40}.arw", "sha1": "0" * 40}]
    noisy = [
        {"filename": f"Bayer_{scene}_ISO{iso}_sha1={'0' * 40}.arw", "sha1": "0" * 40}
        for iso in (400, 1600, 6400, 12800, 25600)
    ]
    dataset = {
        "Bayer": {
            scene: {
                "test_reserve": reserved,
                "unknown_sensor": reserved,
                "clean_images": clean,
                "noisy_images": noisy,
            }
        }
    }
    files = [
        {
            "restricted": False,
            "dataFile": {
                "filename": row["filename"],
                "id": i + 1,
                "filesize": 16,
                "checksum": {"type": "MD5", "value": "0" * 32},
            },
        }
        for i, row in enumerate(clean + noisy)
    ]
    return dataset, files


def test_selection_is_metadata_only_and_keeps_publisher_test_reserve_separate():
    dataset, files = fixture_catalog()
    dataset["Bayer"]["development"]["clean_images"].append(
        {
            "filename": "Bayer_development_GT_ISOUnknown_sha1=unknown.xmp",
            "sha1": "0" * 40,
        }
    )
    result = paired.select_pairs(dataset, files, "development", scenes=["development"])
    assert [r["iso_label"] for r in result[0]["noisy"]] == [1600, 12800]
    assert len(result[0]["clean"]) == 1
    with pytest.raises(ValueError, match="other split"):
        paired.select_pairs(dataset, files, "test", scenes=["development"])
    dataset, files = fixture_catalog("reserved", reserved=True)
    result = paired.select_pairs(dataset, files, "test")
    assert result[0]["unknown_sensor"] and result[0]["scene"] == "reserved"
    with pytest.raises(ValueError, match="other split"):
        paired.select_pairs(dataset, files, "development", scenes=["reserved"])
    # Corrected filename prefixes protect against obsolete publisher split flags.
    dataset, files = fixture_catalog("TEST_protected", reserved=False)
    with pytest.raises(ValueError, match="other split"):
        paired.select_pairs(dataset, files, "development", scenes=["TEST_protected"])


def test_verified_download_reuses_bytes_without_network(tmp_path, monkeypatch):
    payload = b"raw sensor bytes"
    record = descriptor("example.arw", payload)
    monkeypatch.setattr(
        paired.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(payload)
    )
    result = paired.download_file(tmp_path, record)
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert (tmp_path / "example.arw").read_bytes() == payload

    def unavailable(*args, **kwargs):
        raise AssertionError("A verified existing file must not be downloaded again")

    monkeypatch.setattr(paired.urllib.request, "urlopen", unavailable)
    assert paired.download_file(tmp_path, record) == result


def test_invalid_existing_download_is_preserved(tmp_path):
    path = tmp_path / "example.arw"
    path.write_bytes(b"existing bytes")
    with pytest.raises(ValueError, match="checksum mismatch"):
        paired.download_file(tmp_path, descriptor(path.name))
    assert path.read_bytes() == b"existing bytes"


@pytest.mark.parametrize("network_failure", [False, True])
def test_failed_download_cleans_only_its_own_temporary_files(
    tmp_path, monkeypatch, network_failure
):
    record = descriptor("example.arw")
    marker = tmp_path / "unrelated.part"
    marker.write_bytes(b"keep")

    def failed(*args, **kwargs):
        if network_failure:
            raise urllib.error.URLError("offline")
        return io.BytesIO(b"different payload")

    monkeypatch.setattr(paired.urllib.request, "urlopen", failed)
    monkeypatch.setattr(paired.time, "sleep", lambda seconds: None)
    with pytest.raises((ValueError, urllib.error.URLError)):
        paired.download_file(tmp_path, record)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["unrelated.part"]
    assert marker.read_bytes() == b"keep"


def test_publisher_filename_cannot_escape_download_directory(tmp_path):
    with pytest.raises(ValueError, match="Unsafe publisher filename"):
        paired.download_file(tmp_path, descriptor("../escape.arw"))
    assert not list(tmp_path.iterdir())
