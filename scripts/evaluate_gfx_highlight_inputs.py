"""CPU comparisons on the frozen supplementary sign/platform GFX inputs."""

import argparse
import gc
import json
import os
from pathlib import Path

import numpy as np
import torch
from prepare_gfx_highlight_inputs import read, sha

from demosaic.inference import load_checkpoint
from demosaic.reference import load_rawnind, publisher_input_scale
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


@torch.inference_mode()
def main(inputs, input_audit, checkpoints, output, rawnind=None, *, checkpoint_labels=None):
    os.nice(5)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan, audit = read(inputs), read(input_audit)
    assert audit["status"] == "completed-independent-GFX-highlight-input-and-native-preview-audit"
    assert audit["inputs_sha256"] == sha(inputs) and len(audit["cases"]) == 2
    if not checkpoints and rawnind is None:
        raise ValueError("Select a checkpoint or the optional released RawNIND comparator")
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    cached = []
    for case in plan["cases"]:
        assert sha(case["arrays"]) == case["sha256"]
        with np.load(case["arrays"], allow_pickle=False) as loaded:
            cached.append({key: torch.from_numpy(loaded[key].copy()) for key in loaded.files})
    provenance = [
        {"path": str(path), "sha256": sha(path), "kind": "checkpoint"} for path in checkpoints
    ]
    if checkpoint_labels is not None:
        assert set(checkpoint_labels) == {r["sha256"] for r in provenance}
        assert all(isinstance(v, str) and v for v in checkpoint_labels.values())
        assert len(set(checkpoint_labels.values())) == len(checkpoint_labels)
    if rawnind is not None:
        provenance.append(
            {
                "path": str(rawnind),
                "kind": "RawNIND:CFA-channel",
                "sha256": sha(rawnind / "utnet2-bayer.pt"),
                "source": str(rawnind / "raw_denoiser.py"),
                "source_sha256": sha(rawnind / "raw_denoiser.py"),
                "input_scale": publisher_input_scale(
                    plan["metadata"]["white_levels"],
                    plan["metadata"]["black_levels"],
                    plan["metadata"]["adc_white_level"],
                ),
                "clip_input": False,
                "gain": "Per-channel observed-CFA least squares, input only; no reference fitting",
            }
        )
    sources = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    archive = output / "source"
    archive.mkdir()
    for path in [Path(__file__), *map(Path, sources)]:
        (archive / path.name).write_bytes(path.read_bytes())
    execution = {
        "inputs": str(inputs),
        "inputs_sha256": sha(inputs),
        "input_audit": str(input_audit),
        "input_audit_sha256": sha(input_audit),
        "checkpoints": provenance,
        "source_files": sources,
        "driver_sha256": sha(__file__),
        "runtime": "CPU FP32/contiguous/native512/B1/two threads; no autocast or CUDA. Each input loaded once and reused across models.",
        "scope": "Two supplementary real-capture regions fixed without learned outputs. No exact GT or reference scores; ISO100 AHD reference differs in aperture/time/motion/sign content. This is context inference, not a new full-frame result, controlled speed measurement or trained improvement. No training, output fit or promotion.",
    }
    (output / "plan.json").write_text(json.dumps(execution, indent=2) + "\n")
    predictions, crops = [], []
    for index, record in enumerate(provenance):
        if record["kind"] == "checkpoint":
            model, state = load_checkpoint(record["path"], "cpu")
            record.update(
                step=state["step"],
                label=checkpoint_labels[record["sha256"]]
                if checkpoint_labels is not None
                else Path(state["config"]["run"]).name + f":step{state['step']}",
                model_config=model.config.to_dict(),
            )
            del state
        else:
            model = load_rawnind(
                rawnind,
                gain_mode="cfa-channel",
                device="cpu",
                input_scale=record["input_scale"],
                clip_input=False,
            )
            record["label"] = record["kind"]
        model.eval().to(memory_format=torch.contiguous_format)
        for case_index, (case, tensors) in enumerate(zip(plan["cases"], cached, strict=True)):
            if hasattr(model, "set_noise"):
                model.set_noise(plan["conditioning"]["shot"], plan["conditioning"]["read"])
            prediction = model(
                *(tensors[key] for key in ["packed", "variance", "colors", "wb", "matrix"])
            )
            assert prediction.shape == (1, 3, 512, 512) and prediction.dtype == torch.float32
            assert torch.isfinite(prediction).all()
            path = output / f"model{index}-case{case_index}-RGB-f32.npy"
            np.save(path, prediction.numpy(), allow_pickle=False)
            predictions.append(
                {
                    "path": str(path),
                    "sha256": sha(path),
                    "shape": [1, 3, 512, 512],
                    "dtype": "float32",
                    "model_index": index,
                    "case_index": case_index,
                }
            )
            roi = case["ROI_xywh"]
            exposure = plan["display_exposure"]
            panels = []
            for label, rgb, coordinates in [
                ("Noisy (Malvar)", tensors["noisy_rgb"], roi),
                ("Restored / CPU FP32", prediction, roi),
                ("ISO100 AHD / not GT", tensors["reference_rgb"], [0, 0, 160, 160]),
            ]:
                panels.append(
                    (
                        label,
                        display_crop(
                            rgb, tensors["wb"], tensors["matrix"], coordinates, exposure=exposure
                        ),
                    )
                )
            crops.append(
                save_triplet(
                    output,
                    f"model{index}:{case['region']['name']}",
                    panels,
                    caption=case["region"]["name"] + " / " + record["label"],
                    metadata={
                        "model_index": index,
                        "case_index": case_index,
                        "model": record,
                        "source": plan["sources"],
                        "region": case["region"],
                        "context_xywh": case["context_xywh"],
                        "ROI_xywh": roi,
                        "conditioning": plan["conditioning"],
                        "display_exposure": exposure,
                        "white_balance": plan["metadata"]["white_balance"],
                        "camera_to_srgb": plan["metadata"]["camera_to_srgb"],
                        "reference": "Independent DSCF3880 ISO100 f/5.6 AHD reference, not GT; time/motion/sign content differs from DSCF3879 ISO6400 f/1.7.",
                        "checkpoint_sha256": record["sha256"],
                        "runtime": execution["runtime"],
                    },
                )
            )
        print(
            json.dumps({"model_index": index, "label": record["label"], "regions_completed": 2}),
            flush=True,
        )
        del model
        gc.collect()
    assert not torch.cuda.is_initialized()
    for path, digest in sources.items():
        assert sha(path) == digest
    for record in provenance:
        assert (
            sha(
                Path(record["path"]) / "utnet2-bayer.pt"
                if record["kind"] != "checkpoint"
                else record["path"]
            )
            == record["sha256"]
        )
    result = {
        "status": "completed-GFX-highlight-CPU-comparison-awaiting-artifact-and-native-review",
        "plan": str(output / "plan.json"),
        "plan_sha256": sha(output / "plan.json"),
        "checkpoints": provenance,
        "float_predictions": predictions,
        "native_crops": crops,
        "CUDA_initialized": False,
        "quality_scores": None,
        "scope": execution["scope"],
    }
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "report": str(output / "report.json"),
                "predictions": len(predictions),
                "native_triplets": len(crops),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoints", type=Path, nargs="*")
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--input-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rawnind", type=Path)
    main(**vars(parser.parse_args()))
