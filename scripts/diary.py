"""Create local-time diary entries and migrate the audited UTC filename mistakes."""

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL = ZoneInfo("America/Los_Angeles")
REPO = Path(__file__).resolve().parents[1]
STAMP = "%Y-%m-%d-%H-%M-%S"


def local_prefix(instant):
    if instant.tzinfo is None:
        raise ValueError("Diary timestamps must be timezone-aware")
    return instant.astimezone(LOCAL).strftime(STAMP)


def create(root, title, slug):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Use a lowercase hyphen-separated slug")
    now = dt.datetime.now(LOCAL)
    path = root / "diary" / f"{local_prefix(now)}-{slug}.md"
    with path.open("x") as stream:
        stream.write(
            f"# {title}\n\nRecorded: {now.isoformat(timespec='seconds')} (America/Los_Angeles).\n\n"
        )
    return path


def migrate(root, audit, apply=False):
    entries = json.loads(audit.read_text())
    changes = []
    for item in entries:
        if item["kind"] != "UTC-candidate":
            continue
        # This audited cohort is unambiguous: UTC matches filesystem creation
        # within five minutes; interpreting the same prefix as local is ~7h late.
        if abs(item["UTC_delta_minutes"]) > 5 or item["local_delta_minutes"] > -400:
            raise ValueError("Ambiguous diary time requires manual review")
        old, new = root / item["path"], root / item["new_path_if_UTC"]
        if old.parent != root / "diary" or new.parent != root / "diary":
            raise ValueError("Migration must stay in the diary directory")
        if not old.is_file() or new.exists():
            raise ValueError("Missing old diary or destination collision")
        old_time = dt.datetime.strptime(old.name[:19], STAMP).replace(tzinfo=dt.UTC)
        assert new.name[:19] == local_prefix(old_time)
        changes.append(
            {
                "old_path": item["path"],
                "new_path": item["new_path_if_UTC"],
                "content_sha256_unchanged": hashlib.sha256(old.read_bytes()).hexdigest(),
                "filesystem_creation_local": item["birth_local"],
                "UTC_prefix_to_creation_minutes": item["UTC_delta_minutes"],
            }
        )
    if apply:
        manifest = root / "diary/timestamp-corrections.json"
        if manifest.exists():
            raise ValueError("Timestamp migration has already been recorded")
        for item in changes:
            (root / item["old_path"]).rename(root / item["new_path"])
            assert (
                hashlib.sha256((root / item["new_path"]).read_bytes()).hexdigest()
                == item["content_sha256_unchanged"]
            )
        manifest.write_text(
            json.dumps(
                {
                    "timezone": str(LOCAL),
                    "recorded_local": dt.datetime.now(LOCAL).isoformat(),
                    "basis": "84 audited UTC filename prefixes match original filesystem creation within5min and would lie about7h in the future if interpreted as local. Convert the represented instant using ZoneInfo; preserve every Markdown byte. Historical machine receipts retain their literal paths/hashes and can resolve renamed diary files through this mapping.",
                    "corrections": changes,
                },
                indent=2,
            )
            + "\n"
        )
    return changes


def resolve(root, path):
    candidate = Path(path)
    if candidate.is_absolute():
        candidate = candidate.relative_to(root)
    if (root / candidate).exists():
        return root / candidate
    manifest = json.loads((root / "diary/timestamp-corrections.json").read_text())
    for item in manifest["corrections"]:
        if str(candidate) == item["old_path"]:
            return root / item["new_path"]
    raise FileNotFoundError(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    new = sub.add_parser("new")
    new.add_argument("title")
    new.add_argument("--slug", required=True)
    migration = sub.add_parser("migrate")
    migration.add_argument("audit", type=Path)
    migration.add_argument("--apply", action="store_true")
    alias = sub.add_parser("resolve")
    alias.add_argument("path")
    args = parser.parse_args()
    if args.mode == "new":
        print(create(REPO, args.title, args.slug))
    elif args.mode == "migrate":
        print(
            json.dumps(
                {
                    "renamed" if args.apply else "proposed": len(
                        migrate(REPO, args.audit, args.apply)
                    )
                }
            )
        )
    else:
        print(resolve(REPO, args.path))
