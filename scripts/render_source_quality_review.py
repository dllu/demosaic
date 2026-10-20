"""Render source identity and native-pixel views for manual corpus curation."""

import argparse
import hashlib
import io
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps
from train_directional_bank_trial import read, ref, save


def checksum(path, algorithm):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def main(plan_path, candidates, output, *, loss_count=8, proxy_count=4, skip_reviewed=None):
    plan = read(plan_path)
    output.mkdir(parents=True, exist_ok=False)
    operator = output / "renderer-executed-source.py"
    shutil.copyfile(__file__, operator)
    snapshot = output / "candidate-snapshot.json"
    shutil.copyfile(candidates, snapshot)
    ranked = read(snapshot)
    skipped = set()
    if skip_reviewed:
        decisions = output / "previous-decisions.json"
        shutil.copyfile(skip_reviewed, decisions)
        skipped = {r["id"] for r in read(decisions)["sources"]}
    rows = {
        r["id"]: r
        for r in (
            json.loads(line) for line in Path(plan["manifest"]["path"]).read_text().splitlines()
        )
        if r["split"] == "train"
    }
    selected = {}

    def add(record, category):
        if record["id"] in skipped:
            return
        entry = selected.setdefault(record["id"], {"record": record, "categories": []})
        entry["categories"].append(category)

    for name, records in ranked["high_loss"].items():
        for record in records[:loss_count]:
            add(record, "high_loss:" + name)
    for name, records in ranked["IQA_proxies_not_automatic_labels"].items():
        for record in records[:proxy_count]:
            add(record, "proxy:" + name)
    for record in ranked.get("metadata_candidates", [])[:24]:
        add(record, "metadata-title-review-cue")
    for record in list(rows.values())[:4]:
        add({"id": record["id"]}, "unselected-first4-hash-ordered-sources")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    records, images, sheets = [], [], []
    for identity, selected_case in selected.items():
        row, scored = rows[identity], selected_case["record"]
        original = Path("/mnt/external/qi") / row["download_path"]
        cache = Path(row["cache"])
        assert checksum(original, "sha1") == row["sha1_hex"]
        assert checksum(cache, "sha256") == row["cache_sha256"]
        array = np.load(cache, mmap_mode="r", allow_pickle=False)
        h, w = array.shape[:2]
        roi = scored.get("ROI_in_bin4_xywh", [(w - 512) // 2, (h - 512) // 2, 512, 512])
        x, y, width, height = roi
        assert width == height == 512
        crop = array[y : y + height, x : x + width].copy()
        if "actual_bin4_crop_sha256" in scored:
            assert hashlib.sha256(crop.tobytes()).hexdigest() == scored["actual_bin4_crop_sha256"]
        target = crop.astype(np.float32).reshape(256, 2, 256, 2, 3).mean((1, 3)) / 65535
        encoded = np.where(target <= 0.0031308, 12.92 * target, 1.055 * target ** (1 / 2.4) - 0.055)
        binned = Image.fromarray(np.rint(encoded.clip(0, 1) * 255).astype(np.uint8))
        with Image.open(original) as source:
            source = ImageOps.exif_transpose(source)
            profile = source.info.get("icc_profile")
            source = source.convert("RGB")
            if profile:
                source = ImageCms.profileToProfile(
                    source,
                    ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                    ImageCms.createProfile("sRGB"),
                    outputMode="RGB",
                )
            # A centered native source view within the scored source context.
            cx, cy = (
                min(source.width - 128, x * 4 + width * 2),
                min(source.height - 128, y * 4 + height * 2),
            )
            source_roi = [max(0, cx - 128), max(0, cy - 128), 256, 256]
            sx, sy, sw, sh = source_roi
            native = source.crop((sx, sy, sx + sw, sy + sh))
            thumbnail = ImageOps.contain(source, (256, 256), Image.Resampling.LANCZOS)
            context = Image.new("RGB", (256, 256), "#e7e7e7")
            context.paste(thumbnail, ((256 - thumbnail.width) // 2, (256 - thumbnail.height) // 2))
        image = Image.new("RGB", (804, 314), "white")
        draw = ImageDraw.Draw(image)
        title = row["title"]
        draw.text(
            (8, 3),
            identity[:12] + " / " + ", ".join(selected_case["categories"]),
            fill="black",
            font=font,
        )
        draw.text((8, 20), title[:108], fill="black", font=small)
        for j, (view, label) in enumerate(
            [
                (context, "Full source (thumbnail)"),
                (native, "Source native256 / sRGB"),
                (binned, "8x-binned target native256"),
            ]
        ):
            image.paste(view, (8 + j * 266, 50))
            draw.text((8 + j * 266, 35), label, fill="black", font=small)
        name = output / (identity + ".png")
        image.save(name)
        records.append(
            {
                "id": identity,
                "source": row,
                "categories": selected_case["categories"],
                "scored_case": scored,
                "view": ref(name),
                "original_SHA1_verified": True,
                "whole_cache_SHA256_verified": True,
                "bin4_context_xywh": roi,
                "native_source_xywh_after_EXIF_orientation": source_roi,
                "display_exposure": 1,
                "source_display": "ICC to sRGB if present; native crop never resized",
                "binned_display": "linear-sRGB area2 from bin4, sRGB encoding; native256 pixels never resized",
                "classification": "pending-actual-visual-review",
            }
        )
        images.append(image)
    for start in range(0, len(images), 6):
        group = images[start : start + 6]
        board = Image.new("RGB", (804, 314 * len(group)), "#dddddd")
        for i, value in enumerate(group):
            board.paste(value, (0, i * 314))
        path = output / f"source-sheet-{start // 6:02d}.png"
        board.save(path)
        sheets.append({"image": ref(path), "ids": [r["id"] for r in records[start : start + 6]]})
    save(
        output / "index.json",
        {
            "status": "rendered-source-views-awaiting-actual-visual-curation",
            "plan": ref(plan_path),
            "candidate_snapshot": ref(snapshot),
            "sources_scored_at_selection": ranked["sources_scored"],
            "ranking_complete_at_selection": ranked["complete"],
            "selection": {
                "loss_count": loss_count,
                "proxy_count": proxy_count,
                "skipped_previously_reviewed": len(skipped),
            },
            "operator": ref(operator),
            "sources": records,
            "sheets": sheets,
            "scope": "Targeted photographic-source curation, not a restoration-method comparison. Only full-source thumbnails are resized; native source/target pixels retain256x256. No inference or automatic exclusion.",
        },
    )
    print({"sources": len(records), "sheets": len(sheets), "index": str(output / "index.json")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--loss-count", type=int, default=8)
    parser.add_argument("--proxy-count", type=int, default=4)
    parser.add_argument("--skip-reviewed", type=Path)
    args = parser.parse_args()
    assert args.loss_count > 0 and args.proxy_count > 0
    main(
        args.plan.resolve(),
        args.candidates.resolve(),
        args.output.resolve(),
        loss_count=args.loss_count,
        proxy_count=args.proxy_count,
        skip_reviewed=args.skip_reviewed,
    )
