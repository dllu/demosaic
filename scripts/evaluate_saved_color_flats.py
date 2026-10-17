"""Compare checkpoints on frozen exact-target color fields without new draws."""

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch
from audit_colored_flats import metrics

from demosaic.cfa import malvar
from demosaic.inference import load_checkpoint
from demosaic.nonlocal_reference import CHECKPOINT_SHA256, load_nonlocal_reference
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


@torch.inference_mode()
def main(checkpoints, inputs, output, nonlocal_reference=None):
    if not checkpoints and nonlocal_reference is None:
        raise ValueError("Choose at least one checkpoint or the optional RAW reference")
    os.nice(5)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan = read(inputs)
    assert len(plan["cases"]) == 32 and plan["roi_xywh"] == [48, 48, 160, 160]
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "source"
    archive.mkdir()
    sources = {p.name: sha(p) for p in Path("src/demosaic").glob("*.py")}
    for path in [
        Path(__file__),
        Path(__file__).with_name("audit_colored_flats.py"),
        *Path("src/demosaic").glob("*.py"),
    ]:
        (archive / path.name).write_bytes(path.read_bytes())
    provenance = []
    for checkpoint in checkpoints:
        path = Path(checkpoint)
        provenance.append({"path": str(path), "sha256": sha(path), "kind": "joint-checkpoint"})
    if nonlocal_reference is not None:
        provenance.append(
            {
                "path": str(nonlocal_reference),
                "sha256": CHECKPOINT_SHA256,
                "kind": "authors-RAW-reference-plus-Malvar",
            }
        )
    execution = {
        "inputs": str(inputs),
        "input_plan_sha256": sha(inputs),
        "cases": plan["cases"],
        "checkpoints": provenance,
        "source_files": sources,
        "driver_sha256": sha(__file__),
        "ROI_xywh": plan["roi_xywh"],
        "runtime": "CPU FP32, batch1,2threads; no GPU/RAW decoding or new random draws.",
        "scope": "Four chosen uniform colors, two conditions and four CFAs; one draw per case. Palette is post-hoc diagnostic, not an independent quality benchmark. V43 has different training history; no broad or causal model ranking.",
    }
    (output / "plan.json").write_text(json.dumps(execution, indent=2) + "\n")
    results, predictions, crops = [], [], []
    for model_index, record in enumerate(provenance):
        if record["kind"] == "joint-checkpoint":
            assert sha(record["path"]) == record["sha256"]
            model, state = load_checkpoint(record["path"], "cpu")
            record.update(
                step=state["step"],
                label=f"{Path(state['config']['run']).name}:step{state['step']}",
                model_config=model.config.to_dict(),
            )
            del state
            restored_label = f"Restored / step{record['step']}"
        else:
            model = load_nonlocal_reference(record["path"], device="cpu", archive=output)
            record.update(label=model.receipt["label"], reference_receipt=model.receipt)
            assert record["sha256"] == model.receipt["sha256"]
            restored_label = "Restored / authors RAW"
        model.eval().to(memory_format=torch.contiguous_format)
        for case_index, case in enumerate(plan["cases"]):
            assert sha(case["arrays"]) == case["sha256"]
            with np.load(case["arrays"], allow_pickle=False) as values:
                arrays = {k: values[k].copy() for k in values.files}
            batch = {k: torch.from_numpy(v) for k, v in arrays.items()}
            condition = case["condition"]
            model.set_noise(condition["shot"], condition["read"])
            prediction = model(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
            assert (
                prediction.shape == (1, 3, 256, 256)
                and prediction.dtype == torch.float32
                and torch.isfinite(prediction).all()
            )
            path = output / f"model{model_index}-case{case_index}-RGB-f32.npy"
            values = prediction.numpy()
            np.save(path, values, allow_pickle=False)
            predictions.append(
                {
                    "path": str(path),
                    "sha256": sha(path),
                    "shape": [1, 3, 256, 256],
                    "dtype": "float32",
                    "model_index": model_index,
                    "case": case_index,
                }
            )
            results.append(
                {
                    "model_index": model_index,
                    "case": case_index,
                    "palette": case["palette"],
                    "condition": condition["name"],
                    "pattern": case["pattern"],
                    "metrics": metrics(values, arrays),
                }
            )
            if (
                case["palette"] in ["neutral", "fabric-mean"]
                and condition["name"] == "iso12800-prior"
                and case["pattern"] == "RGGB"
            ):
                noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
                crops.append(
                    save_triplet(
                        output,
                        f"{model_index}:{case['id']}",
                        [
                            (
                                label,
                                display_crop(rgb, batch["wb"], batch["matrix"], plan["roi_xywh"]),
                            )
                            for label, rgb in [
                                ("Noisy (Malvar)", noisy),
                                (restored_label, prediction),
                                ("GT (analytic)", batch["target"]),
                            ]
                        ],
                        caption=case["id"] + " / " + record["label"] + " / CPU FP32",
                        metadata={
                            "case": case,
                            "model": record,
                            "ROI_xywh": plan["roi_xywh"],
                            "white_balance": plan["white_balance"],
                            "camera_to_srgb": plan["camera_to_srgb"],
                            "conditioning": condition,
                            "display_exposure": 1.0,
                            "reference": "Exact uniform analytic target, not a real photograph or a newly sampled degradation.",
                        },
                    )
                )
        print(
            json.dumps({"model_index": model_index, "model": record, "cases_completed": 32}),
            flush=True,
        )
        del model
        gc.collect()
    assert len(results) == len(predictions) == 32 * len(provenance) and len(crops) == 2 * len(
        provenance
    )
    assert not torch.cuda.is_initialized()
    assert all(sha(Path("src/demosaic") / name) == digest for name, digest in sources.items())
    report = {
        "status": "completed-saved-color-flat-CPU-inference-awaiting-audit-and-native-review",
        "plan": str(output / "plan.json"),
        "plan_sha256": sha(output / "plan.json"),
        "checkpoints": provenance,
        "results": results,
        "float_predictions": predictions,
        "native_crops": crops,
        "CUDA_initialized": False,
        "scope": execution["scope"],
        "limitations": "One observation per color/condition/CFA. No new training, output correction, target fit, photographic score, convergence or real-camera quality conclusion.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(output / "report.json"),
                "predictions": len(predictions),
                "PNGs": len(crops),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, nargs="*")
    parser.add_argument("--nonlocal-reference", type=Path)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.checkpoint, args.inputs, args.output, args.nonlocal_reference)
