"""View matched arms with method-specific checkpoint/state metadata at 100%."""

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

import build_native_crop_viewer as original
from PIL import Image

DEFAULT_A = "V183-coherent-pair-EMA"
DEFAULT_B = "V184-wave-readout-EMA"


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Existing viewer template changed; inspect before adapting")
    return text.replace(old, new)


def template(fixture):
    text = replace_once(
        original.TEMPLATE,
        "const latest=row.predictions.find(label=>label.endsWith('EMA'))||labels[labels.length-1];",
        "const latest=labels.includes(data.defaults.b)?data.defaults.b:row.predictions.find(label=>label.endsWith('EMA'))||labels[labels.length-1];",
    )
    text = replace_once(
        text,
        "const prior=labels.filter(label=>/V[0-9]+[- ]EMA/.test(label)&&label!==latest).at(-1)||labels[1];",
        "const prior=labels.includes(data.defaults.a)?data.defaults.a:labels[1];",
    )
    text = replace_once(
        text,
        "`${label} checkpoint SHA256 ${data.checkpoints[label]}`",
        "`${label}: ${data.checkpoints[label]}`",
    )
    if fixture:
        text = replace_once(
            text,
            "<h1>Denoising at 100%</h1>",
            "<h1>CPU LAYOUT FIXTURE — reused pixels, no V184 quality</h1>",
        )
        text = replace_once(
            text,
            "<title>Native denoising comparisons</title>",
            "<title>CPU layout fixture; no V184 quality</title>",
        )
    return text


def checkpoint_descriptions(entries):
    descriptions = {}
    for method, entry in entries.items():
        state = entry["state"]
        if state not in ["raw", "EMA"] or not method.endswith(("-" + state, " " + state)):
            raise ValueError("Method label and checkpoint state disagree")
        checkpoint = entry["source_checkpoint"]
        if not all(
            re.fullmatch(r"[0-9a-f]{64}", digest)
            for digest in [checkpoint["sha256"], entry["module_hash"]]
        ):
            raise ValueError("Expected checkpoint and module-state SHA256 values")
        descriptions[method] = (
            f"{state} state\nSource checkpoint SHA256 {checkpoint['sha256']}\n"
            f"Module-state SHA256 {entry['module_hash']}"
        )
    return descriptions


def build(manifest, output, report, *, method_a=DEFAULT_A, method_b=DEFAULT_B):
    data = json.loads(manifest.read_text())
    checkpoints = checkpoint_descriptions(data["method_checkpoints"])
    if method_a == method_b or not all(method in checkpoints for method in [method_a, method_b]):
        raise ValueError("Expected two distinct comparison methods with checkpoint metadata")
    cases = []
    predicted_methods = set()
    for item in data["images"]:
        if item["triplet"]:
            continue
        if not item["no_resize"]:
            raise ValueError("Expected native pixels")
        image = Path(item["image"]["path"])
        if (
            image.parent != output.parent
            or hashlib.sha256(image.read_bytes()).hexdigest() != item["image"]["sha256"]
        ):
            raise ValueError("Source image path/hash differs from manifest")
        with Image.open(image) as pixels:
            width, height = pixels.size
        labels = [panel["label"] for panel in item["panels"]]
        if len(set(labels)) != len(labels) or not all(
            method in labels for method in [method_a, method_b]
        ):
            raise ValueError("Expected unique panels and both matched methods in each board")
        predictions = list(item["predictions"])
        if not predictions or not set(predictions) <= set(labels) & set(checkpoints):
            raise ValueError("Every predicted method needs its own checkpoint metadata and panel")
        predicted_methods.update(predictions)
        for panel in item["panels"]:
            x, y, w, h = panel["xywh"]
            if not (w == h == 160 and 0 <= x <= width - w and 0 <= y <= height - h):
                raise ValueError("Expected valid 160×160 native panel coordinates")
        cases.append(
            {
                "id": item["case"]["id"],
                "image": quote(image.name),
                "roi": item["ROI_xywh"],
                "anchor": item["anchor"],
                "exposure": item["exposure"],
                "contrast": item["contrast"],
                "panels": item["panels"],
                "predictions": predictions,
            }
        )
    if not cases or not {method_a, method_b} <= predicted_methods:
        raise ValueError("Expected native comparisons for both default methods")
    payload = json.dumps(
        {
            "cases": cases,
            "checkpoints": checkpoints,
            "defaults": {"a": method_a, "b": method_b},
            "fixture": bool(data.get("fixture", False)),
        },
        ensure_ascii=True,
    ).replace("<", "\\u003c")
    rendered = template(bool(data.get("fixture", False))).replace("__DATA__", payload)
    rendered = rendered.replace("__REPORT__", html.escape(report, quote=True))
    with output.open("x") as stream:
        stream.write(rendered)
    print(
        f"Built {len(cases)} native cases; {method_a} vs {method_b}; fixture={bool(data.get('fixture', False))}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", required=True)
    parser.add_argument("--method-a", default=DEFAULT_A)
    parser.add_argument("--method-b", default=DEFAULT_B)
    args = parser.parse_args()
    build(
        args.manifest.resolve(),
        (args.output or args.manifest.with_name("native-viewer.html")).resolve(),
        args.report,
        method_a=args.method_a,
        method_b=args.method_b,
    )
