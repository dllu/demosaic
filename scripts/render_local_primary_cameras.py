"""Native local-model camera comparisons using the established first-crop rule."""

import argparse
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw

from demosaic.cfa import malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.reporting import display_crop, save_triplet


@torch.inference_mode()
def render_panel(result_path, output):
    result_path, output = Path(result_path).resolve(), Path(output).resolve()
    result = read_json(result_path)
    plan = read_json(checked(result["plan"]))
    canonical_collection = read_json(checked(plan["canonical_inputs"]))
    physical_plan = read_json(checked(canonical_collection["plan"]))
    manifest = read_json(checked(physical_plan["stages"][result["stage"]]["manifest"]))
    output.mkdir(parents=True)
    boards, triplets = [], []
    labels = {arm: spec.get("display_label", arm + " EMA") for arm, spec in plan["models"].items()}
    candidate = next(arm for arm in labels if arm != plan["parent_label"])
    candidate_panel = 1 + list(labels).index(candidate)
    for item in result["native_selection"]:
        case = read_json(checked(item["case"]))
        canonical, index = item["canonical"], item["sample"]
        with np.load(checked(canonical["arrays"]), allow_pickle=False) as data:
            batch = {k: torch.from_numpy(data[k].copy()) for k in data.files}
        predictions = {v["arm"]: torch.from_numpy(np.load(checked(v["prediction"]), allow_pickle=False)) for v in case["variants"]}
        roi = [176, 176, 160, 160]
        wb, matrix = batch["wb"][index:index+1], batch["matrix"][index:index+1]

        def display(tensor, index=index, wb=wb, matrix=matrix, roi=roi):
            return display_crop(tensor[index:index+1], wb, matrix, roi, exposure=1.0)

        noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
        panels = [("Noisy (Malvar)", display(noisy)),
                  *[(labels[arm], display(predictions[arm])) for arm in labels],
                  ("Independent AHD ref", display(batch["reference_rgb"]))]
        image = Image.new("RGB", (8 + 168 * len(panels), 192), "#eeeeee")
        draw, rectangles = ImageDraw.Draw(image), []
        for i, (label, values) in enumerate(panels):
            assert values.shape == (160, 160, 3) and np.isfinite(values).all()
            x = 8 + 168 * i
            pixels = np.rint(values.clip(0, 1) * 255).astype(np.uint8)
            draw.text((x, 5), label, fill="black")
            image.paste(Image.fromarray(pixels), (x, 24))
            rectangles.append({"label": label, "png_xywh": [x, 24, 160, 160]})
        key = result["stage"] + "-" + canonical["context"]["scene"]
        path = output / (key + ".png")
        image.save(path)
        reread = np.asarray(Image.open(path))
        for panel, (_, values) in zip(rectangles, panels, strict=True):
            x, y, w, h = panel["png_xywh"]
            np.testing.assert_array_equal(reread[y:y+h, x:x+w], np.rint(values.clip(0, 1) * 255).astype(np.uint8))
        x, y, w, h = canonical["context"]["crop_xywh"][index]
        capture = manifest["cases"][canonical["context"]["case_index"]]
        metadata = {
            "id": key, "selection": item["selection"], "analysis": reference(result_path),
            "case": item["case"], "canonical_arrays": canonical["arrays"],
            "native_context_xywh": [x, y, w, h], "ROI_xywh": roi,
            "absolute_native_ROI_xywh": [x+176, y+176, 160, 160],
            "source_noisy_RAW": canonical["context"]["raw_source"],
            "capture_metadata": capture["metadata"], "conditioning": canonical["context"]["noise"],
            "CFA_pattern": canonical["context"]["pattern"], "WB": wb[0].tolist(),
            "camera_to_sRGB": matrix[0].tolist(), "display_exposure": 1.0,
            "models": result["models"], "weights": "EMA",
            "reference": "Independent low-noise/aligned reference demosaiced with AHD; auxiliary RGB comparison, not exact RGB GT. Primary numerical score uses only the measured-CFA reference mask.",
        }
        boards.append({"image": reference(path), "panels": rectangles, **metadata})
        triplet = save_triplet(output / "triplets", key,
                               [panels[0], (labels[candidate], panels[candidate_panel][1]), panels[-1]],
                               caption=key, metadata=metadata)
        triplets.append({"id": key, "image": reference(output / "triplets" / triplet["image"]),
                         "metadata": reference((output / "triplets" / triplet["image"]).with_suffix(".json"))})
    write_json(output / "result.json", {
        "renderer": reference(__file__), "analysis": reference(result_path), "boards": boards, "triplets": triplets,
        "pixel_size": [160, 160], "actual_viewing": "pending",
        "scope": "First capture/first crop of every fixed camera scene, center160 ROI, same noisy observation/coordinates/display across methods, no resizing. Every PNG panel checked against rendered saved tensors. No new neural/GPU/noise/RAW/optimizer calls. Real independent AHD reference is not exact RGB GT; native viewing separate.",
    })
    print("Rendered", result["stage"], len(boards), "native boards and", len(triplets), "reference triplets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, [2, 3])
    torch.set_num_threads(2)
    render_panel(args.result, args.output)
