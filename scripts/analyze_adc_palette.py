"""Compare fixed physical ADC policies on the complete 588-case saved palette."""

import argparse
import os
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
import torch

from demosaic.adc_bins import adc_bin_bounds, adc_bin_projection
from demosaic.archive_metrics import color
from demosaic.cfa import adc_cfa_projection, mosaic
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.prediction_archive import fingerprint


@torch.inference_mode()
def analyze(plan_path):
    plan = read_json(plan_path)
    source = read_json(checked(plan["palette_plan"]))
    collection = read_json(checked(plan["palette_collection"]))
    assert collection["plan"] == plan["palette_plan"]
    assert collection["models"] == source["models"]
    assert collection["CPU_rng_unchanged"]
    assert collection["full_model_before"] == collection["full_model_after"]
    assert source["calibration"] == {"bits": 16, "black": .03, "CPU_quantizer_precision": "float32"}
    assert all(v == {"root": 588} for v in collection["root_calls"].values())
    assert collection["local_DINO"] == {"requests": 1176, "executions": 588, "replays": 588}
    assert len(source["observations"]) == len(collection["records"]) == 588
    assert len({o["source_id"] for o in source["observations"]}) == 147
    for path, digest in plan["frozen_files"].items():
        checked({"path": path, "sha256": digest})
    assert not torch.cuda.is_initialized()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    torch.set_num_threads(2)
    root = Path(plan["root"])
    output = root / "output"
    output.mkdir()
    native = read_json(checked(plan["legacy_native_plan"]))
    legacy_collection = read_json(checked(plan["legacy_native_collection"]))
    legacy_cases = {read_json(checked(r))["id"]: read_json(checked(r))
                    for r in legacy_collection["records"]}
    controls = {o["arrays"]["sha256"]: legacy_cases[o["id"]]
                for o in native["observations"] if o["kind"] == "color-spot-check"}
    rng = torch.get_rng_state().clone()
    module_calls = []

    def forbid_module(module, _arguments):
        module_calls.append(type(module).__name__)
        raise RuntimeError("Palette postprocessing must not run a neural module")

    hook = torch.nn.modules.module.register_module_forward_pre_hook(forbid_module)
    rows, files, controls_checked = [], [], 0
    for index, (observation, binding) in enumerate(zip(
        source["observations"], collection["records"], strict=True
    )):
        if (psutil.virtual_memory().available < 24 * 2**30
                or shutil.disk_usage(root).free < 192 * 2**30):
            raise RuntimeError("Physical palette analysis resource reserve reached")
        case = read_json(checked(binding))
        assert case["id"] == observation["id"]
        with np.load(checked(observation["arrays"]), allow_pickle=False) as data:
            arrays = {k: data[k].copy() for k in ("packed", "variance", "colors", "wb", "matrix")}
        assert {k: fingerprint(v) for k, v in arrays.items()} == case["input_fingerprints"]
        packed, colors, wb = [torch.from_numpy(arrays[k]) for k in ("packed", "colors", "wb")]
        low, high = adc_bin_bounds(packed, bit_depth=16, black_level=.03,
                                  quantizer_precision="float32")
        predictions = {}
        for variant in case["variants"]:
            model = variant["label"]
            assert variant["checkpoint"] == source["models"][model]["checkpoint"]
            raw = np.load(checked(variant["prediction"]), allow_pickle=False)
            before = fingerprint(raw)
            if observation["arrays"]["sha256"] in controls:
                previous = next(v for v in controls[observation["arrays"]["sha256"]]["variants"]
                                if v["label"] == model)
                assert previous["checkpoint"] == variant["checkpoint"]
                np.testing.assert_array_equal(raw, np.load(checked(previous["prediction"])))
                controls_checked += 1
            tensor = torch.from_numpy(raw)
            values = {
                "raw": raw,
                "exact-Malvar": adc_cfa_projection(tensor, packed, colors, wb, mode="malvar").numpy(),
                "exact-sites": adc_cfa_projection(tensor, packed, colors, wb, mode="sites").numpy(),
                "ADC-bins": adc_bin_projection(
                    tensor, packed, colors, wb, bit_depth=16, black_level=.03,
                    quantizer_precision="float32", shot=0., read=0.
                ).numpy(),
            }
            assert before == fingerprint(raw)
            assert all(v.dtype == np.float32 and v.shape == (1, 3, 256, 256)
                       and np.isfinite(v).all() for v in values.values())
            path = output / f"physical-{index:03d}-{model}.npz"
            with path.open("xb") as stream:
                np.savez(stream, **{k: v for k, v in values.items() if k != "raw"})
            files.append({"id": observation["id"], "model": model,
                          "raw_prediction": variant["prediction"], "physical_arrays": reference(path)})
            predictions[model] = values
        # Targets are first decoded after all input-only physical corrections.
        with np.load(checked(observation["target"]), allow_pickle=False) as data:
            target = data["target"].copy()
        arrays["target"] = target
        gt = mosaic(torch.from_numpy(target), colors)
        assert ((gt >= low) & (gt <= high)).all()
        for model, values in predictions.items():
            measured = mosaic(torch.from_numpy(values["ADC-bins"]), colors)
            before = mosaic(torch.from_numpy(values["raw"]), colors)
            assert ((measured >= low) & (measured <= high)).all()
            assert ((measured.double() - gt.double()).square()
                    <= (before.double() - gt.double()).square()).all()
            for policy, value in values.items():
                metrics = color(value, arrays)
                rows.append({"id": observation["id"], "source_id": observation["source_id"],
                             "pattern": observation["pattern"], "model": model, "policy": policy,
                             "mean_bias_DN16": 65535 * max(abs(x) for x in metrics["camera_RGB_mean_error"]),
                             "centered_RMS_DN16": 65535 * metrics["spatially_centered_camera_RGB_RMS"],
                             **metrics})
        write_json(root / "progress.json", {"completed": index + 1, "planned": 588,
                   "metric_rows": len(rows), "legacy_controls_bitexact": controls_checked}, replace=True)
    hook.remove()
    assert not module_calls and not torch.cuda.is_initialized()
    assert torch.equal(rng, torch.get_rng_state())
    assert len(rows) == 4704 and len(files) == 1176 and controls_checked == 16
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["model"], row["policy"]].append(row)
    summary = []
    for (model, policy), values in grouped.items():
        assert len(values) == 588
        bias = max(values, key=lambda r: r["mean_bias_DN16"])
        spatial = max(values, key=lambda r: r["centered_RMS_DN16"])
        summary.append({"model": model, "policy": policy,
                        "max_bias_DN16": bias["mean_bias_DN16"], "max_bias_case": bias["id"],
                        "max_centered_RMS_DN16": spatial["centered_RMS_DN16"],
                        "max_centered_RMS_case": spatial["id"],
                        "mean_camera_RGB_MSE": float(np.mean([r["camera_RGB_MSE"] for r in values]))})
    write_json(root / "result.json", {
        "producer": reference(__file__), "plan": reference(plan_path), "metrics": rows,
        "arrays": files, "summary": summary, "legacy16_predictions_bitexact": controls_checked,
        "module_forwards": len(module_calls), "CPU_RNG_unchanged": True,
        "scope": "All588 pre-existing ADC-only cases/147 colors/four CFAs,all8 fixed EMA/policy"
                 " combinations.3528 physical corrections retained,4704 full color rows. Targets"
                 " decoded after input-only corrections; all target-bin/sample-error constraints checked."
                 " Sixteen overlapping raw predictions match closed CPU native controls exactly."
                 " No new neural/GPU/RAW/noise/optimizer calls or default change. Native viewing"
                 " and independent audit separate; not a general photo/fine-detail benchmark.",
    })
    print("Complete588-case palette", summary, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    analyze(parser.parse_args().plan)
