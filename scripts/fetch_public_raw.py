"""Acquire explicitly CC0 low-ISO RAW candidates into quarantine, never training."""

import argparse
import fcntl
import hashlib
import json
import re
import shutil
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

from demosaic import paired, safety
from demosaic.paired import download_file
from demosaic.safety import writable_path

CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.hrefs, self.checksums = [], []
        self.in_checksum = False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.hrefs.append(attrs["href"])
        if tag == "span":
            self.in_checksum = attrs.get("title", "").lower() == "sha256 checksum"

    def handle_endtag(self, tag):
        if tag == "span":
            self.in_checksum = False

    def handle_data(self, data):
        if self.in_checksum and re.fullmatch("[0-9a-fA-F]{64}", data.strip()):
            self.checksums.append(data.strip().lower())


def select_candidates(survey_path, catalog_path):
    survey = json.loads(Path(survey_path).read_text())
    if checksum(catalog_path) != survey["catalog_sha256"]:
        raise ValueError("Survey/catalog checksum mismatch")
    catalog = json.loads(Path(catalog_path).read_text())["data"]
    records, identities = [], set()
    for candidate in survey["scouted"]:
        matches = [
            r
            for r in catalog
            if r[:3] == [candidate[k] for k in ["make", "model", "mode"]]
            and r[7] == candidate["raw_link_html"]
        ]
        if len(matches) != 1 or candidate["license_url"] != CC0:
            raise ValueError("Candidate does not identify one explicit CC0 catalog entry")
        row = matches[0]
        if CC0 not in Links(row[5]).hrefs:
            raise ValueError("Catalog entry is not explicitly CC0")
        if candidate["metadata_url"] not in Links(row[8]).hrefs:
            raise ValueError("Scouted metadata URL differs from its catalog entry")
        link = Links(row[7])
        if len(link.hrefs) != 1 or len(link.checksums) != 1:
            raise ValueError("Expected one RAW link and published SHA256")
        url = urllib.parse.urlparse(link.hrefs[0])
        identity = re.fullmatch(r"/getfile.php/(\d+)/nice/[^/]+", url.path)
        if url.scheme != "https" or url.netloc != "raw.pixls.us" or not identity:
            raise ValueError("Unexpected RAW host/path")
        identifier = identity[1]
        if identifier in identities:
            raise ValueError("Duplicate candidate file ID")
        identities.add(identifier)
        suffix = Path(url.path).suffix.lower()
        if suffix not in {
            ".nef",
            ".raf",
            ".dng",
            ".arw",
            ".rw2",
            ".cr2",
            ".cr3",
            ".pef",
            ".orf",
            ".srw",
            ".nrw",
        }:
            raise ValueError("Unexpected RAW file extension")
        metadata = Path(candidate["metadata_file"])
        if checksum(metadata) != candidate["metadata_sha256"]:
            raise ValueError("Scouted metadata checksum changed")
        text = metadata.read_text()
        iso = re.search(r"^Exif\.Photo\.ISOSpeedRatings\s+(\d+)\s*$", text, re.MULTILINE)
        if not iso or not 0 < int(iso[1]) <= 200:
            raise ValueError("Candidate metadata does not establish low ISO")
        model = re.sub(r"\s+", "", candidate["model"]).upper()
        if re.search(r"DSCF(?:3842|3879|3880|3883)", text, re.IGNORECASE) or (
            model == "GFX100S" and "2023:12:31" in text
        ):
            raise ValueError("Standing GFX capture family cannot be acquired for training")
        records.append(
            {
                "file_id": int(identifier),
                "filename": identifier + suffix,
                "url": urllib.parse.quote(link.hrefs[0], safe=":/?=&%"),
                "publisher_checksum": {"type": "SHA-256", "value": link.checksums[0]},
                "license": "CC0-1.0",
                "license_url": CC0,
                "make": row[0],
                "model": row[1],
                "catalog_mode": row[2],
                "catalog_row": row,
                "metadata_path": str(metadata.resolve()),
                "metadata_url": candidate["metadata_url"],
                "metadata_sha256": candidate["metadata_sha256"],
                "scouted_iso": int(iso[1]),
            }
        )
    if not records:
        raise ValueError("No candidates selected")
    return records


def fetch_public_raw(survey, catalog, output, *, workers=2):
    if workers not in (1, 2):
        raise ValueError("Use one or two acquisition workers")
    selected = select_candidates(survey, catalog)  # Fail before any network I/O.
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".fetch.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another public RAW acquisition owns this output") from None
        code = [Path(__file__), Path(paired.__file__), Path(safety.__file__)]
        recipe = {
            "survey_sha256": checksum(survey),
            "catalog_sha256": checksum(catalog),
            "implementation": {p.name: checksum(p) for p in code},
        }
        recipe_path = output / "recipe.json"
        if recipe_path.exists() and json.loads(recipe_path.read_text()) != recipe:
            raise ValueError("Acquisition recipe changed; choose a new output")
        recipe_path.write_text(json.dumps(recipe, indent=2) + "\n")
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for path in code + [Path(survey), Path(catalog)]:
            (archive / path.name).write_bytes(path.read_bytes())
        metadata_archive = output / "metadata"
        metadata_archive.mkdir(exist_ok=True)
        for record in selected:
            original = Path(record["metadata_path"])
            copy = metadata_archive / f"exif-{record['file_id']}.txt"
            if copy.exists() and checksum(copy) != record["metadata_sha256"]:
                raise ValueError("Archived metadata checksum changed")
            if not copy.exists():
                copy.write_bytes(original.read_bytes())
            record["metadata_origin_path"] = str(original)
            record["metadata_path"] = str(copy)
        previous = {}
        if (output / "manifest.json").exists():
            previous = {
                r["file_id"]: r for r in json.loads((output / "manifest.json").read_text())["files"]
            }

        def fetch(record):
            if record["file_id"] in previous:
                size = previous[record["file_id"]]["bytes"]
            else:
                with urllib.request.urlopen(
                    urllib.request.Request(record["url"], method="HEAD"), timeout=60
                ) as response:
                    size = int(response.headers["Content-Length"])
            if not 0 < size <= 512 * 1024**2:
                raise ValueError("Unexpected RAW byte count")
            if shutil.disk_usage(output).free < 512 * 1024**3 + 2 * size:
                raise RuntimeError("Public RAW acquisition reached its 512GiB reserve")
            result = download_file(output / "files", {**record, "bytes": size})
            print(
                json.dumps(
                    {"event": "public-raw-verified", "id": result["file_id"], "bytes": size}
                ),
                flush=True,
            )
            return result

        with ThreadPoolExecutor(max_workers=workers) as pool:
            acquired = list(pool.map(fetch, selected))
        result = {
            "format_version": 1,
            "usage": "Quarantine only; NOT a training manifest. Actual decoding, metadata checks and protected-scene/near-duplicate audit required before admission.",
            "recipe": recipe,
            "files": acquired,
            "bytes": sum(r["bytes"] for r in acquired),
        }
        temporary = output / "manifest.json.tmp"
        temporary.write_text(json.dumps(result, indent=2) + "\n")
        temporary.replace(output / "manifest.json")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    result = fetch_public_raw(**vars(parser.parse_args()))
    print(json.dumps({"files": len(result["files"]), "bytes": result["bytes"]}), flush=True)


if __name__ == "__main__":
    main()
