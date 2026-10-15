import json

import numpy as np
from PIL import Image, ImageDraw

from demosaic.audit import audit_split


def test_split_audit_excludes_train_links_and_validation_exposed_test_images(tmp_path):
    def image(seed):
        rng = np.random.default_rng(seed)
        canvas = Image.new("RGB", (256, 256), (20, 30, 50))
        draw = ImageDraw.Draw(canvas)
        for _ in range(20):
            x, y, width, height = rng.integers(0, 180, 4).tolist()
            draw.rectangle(
                (x, y, x + width, y + height), fill=tuple(rng.integers(20, 240, 3).tolist())
            )
        return np.array(canvas).astype(np.uint16) * 257

    a, b, c = image(1), image(2), image(3)
    samples = [
        ("train-a", "train", a),
        ("val-a", "val", np.rot90(a[:, ::-1])),
        ("val-b", "val", b),
        ("test-b", "test", b),
        ("test-c", "test", c),
    ]
    rows = []
    for identity, split, array in samples:
        path = tmp_path / f"{identity}.npy"
        np.save(path, array)
        rows.append({"id": identity, "split": split, "cache": path.name})
    manifest = tmp_path / "input.jsonl"
    manifest.write_text("".join(json.dumps(r) + "\n" for r in rows))
    before = manifest.read_bytes()
    report = audit_split(manifest, tmp_path / "audit")
    assert report["counts"] == {"train": 1, "excluded": 2, "val": 1, "test": 1}
    assert {r["id"] for r in report["excluded"]} == {"val-a", "test-b"}
    assert manifest.read_bytes() == before
