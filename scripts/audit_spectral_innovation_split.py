"""Independent Torch/CPU arithmetic audit of the NumPy oracle decomposition."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch
from prepare_bank_report_assets import validate_board

from demosaic.cfa import malvar, mosaic
from demosaic.color import render


def ref(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def read(path):
    return json.loads(Path(path).read_text())


def checked(item):
    assert ref(item["path"]) == item
    return Path(item["path"])


def psnr(a, b):
    return -10 * (a - b).square().mean((1, 2, 3)).clamp_min(1e-12).log10()


def main(root):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    rng = torch.get_rng_state().clone()
    plan, prepared, scores = [
        read(root / p) for p in ["plan.json", "preparation.json", "scores.json"]
    ]
    for item in plan["inputs"]:
        checked(item)
    keyed = {(r["condition"], r["source_id"], r["region"]): r for r in scores["rows"]}
    max_fft = max_mhc = max_terms = max_mse = max_psnr = 0.0
    metric_count = term_count = originals = 0
    measured_contractions = []
    for entry, original in zip(prepared["results"], plan["photo_results"], strict=True):
        with np.load(checked(entry["arrays"]), allow_pickle=False) as npz:
            a = {k: torch.from_numpy(npz[k].copy()) for k in npz.files}
        with np.load(checked(original["arrays"]), allow_pickle=False) as old:
            assert all(
                a[k].numpy().tobytes(order="C") == old[k].tobytes(order="C") for k in old.files
            )
            originals += len(old.files)
        colors = a["colors"]
        base, target = a["base"].double(), a["target"].double()
        sampled_base, sampled_target = mosaic(base, colors), mosaic(target, colors)
        sampled_input = a["packed"].double()
        for key, residual in [
            ("target_term", sampled_target - sampled_base),
            ("discrepancy_term", sampled_input - sampled_target),
        ]:
            filtered = torch.fft.irfft2(
                torch.fft.rfft2(residual, norm="ortho") * a["mask"].double(),
                s=residual.shape[-2:],
                norm="ortho",
            )
            max_fft = max(max_fft, float((mosaic(a[key], colors) - filtered).abs().max()))
            actual = malvar(filtered, colors, a["wb"])
            max_mhc = max(max_mhc, float((actual.double() - a[key]).abs().max()))
        for name, component in [
            ("oracle_target", "target_term"),
            ("oracle_discrepancy", "discrepancy_term"),
        ]:
            assert torch.equal(a[name], base + a[component])
        # A*K=I and 0<=mask<=1 give a global measured-CFA L2 contraction
        # for the target-derived term, not an RGB or local-ROI guarantee.
        before = (sampled_base - sampled_target).square().mean((1, 2, 3))
        after = (mosaic(a["oracle_target"], colors) - sampled_target).square().mean((1, 2, 3))
        assert torch.all(after <= before + 1e-14)
        measured_contractions.append(
            {"condition": entry["condition"], "before": before.tolist(), "after": after.tolist()}
        )
        sources = list(dict.fromkeys(row["source_id"] for row in original["cases"]))
        for region, (x, y, w, h) in [
            ("evaluation240", [8, 8, 240, 240]),
            ("native160", [48, 48, 160, 160]),
        ]:
            trimmed = {
                k: v[..., y : y + h, x : x + w].double()
                for k, v in a.items()
                if v.ndim == 4 and v.shape[1] == 3
            }
            e, s, d = (
                trimmed["base"] - trimmed["target"],
                trimmed["target_term"],
                trimmed["discrepancy_term"],
            )
            terms = {
                "base_MSE": e.square().mean((1, 2, 3)),
                "target_component_MSE_change": (2 * e * s + s.square()).mean((1, 2, 3)),
                "discrepancy_component_MSE_change_alone": (2 * e * d + d.square()).mean((1, 2, 3)),
                "component_cross_term": (2 * s * d).mean((1, 2, 3)),
                "target_component_energy": s.square().mean((1, 2, 3)),
                "discrepancy_component_energy": d.square().mean((1, 2, 3)),
                "discrepancy_increment_after_target": (2 * (e + s) * d + d.square()).mean(
                    (1, 2, 3)
                ),
                "decomposed_unit_MSE": (e + s + d).square().mean((1, 2, 3)),
            }
            for i, source in enumerate(sources):
                row = keyed[entry["condition"], source, region]
                for key, values in terms.items():
                    max_terms = max(max_terms, abs(float(values[i]) - row["MSE_terms"][key]))
                    term_count += 1
            for mode in ["full", "base", "unit", "oracle_target", "oracle_discrepancy"]:
                p, t = trimmed[mode], trimmed["target"]
                # Use the frozen original FP32 renderer, independently of the
                # main diagnostic's NumPy FP64 rendering and log reduction.
                rendered_p = render(p.float(), a["wb"], a["matrix"]).double()
                rendered_t = render(t.float(), a["wb"], a["matrix"]).double()
                metrics = {
                    "unclipped_camera_MSE": (p - t).square().mean((1, 2, 3)),
                    "linear_psnr": psnr(p.clamp(0, 1), t.clamp(0, 1)),
                    "srgb_psnr": psnr(rendered_p, rendered_t),
                }
                for i, source in enumerate(sources):
                    row = keyed[entry["condition"], source, region]
                    for key, values in metrics.items():
                        error = abs(float(values[i]) - row["metrics"][mode][key])
                        if key == "unclipped_camera_MSE":
                            max_mse = max(max_mse, error)
                        else:
                            max_psnr = max(max_psnr, error)
                        metric_count += 1
    assert metric_count == 420 and term_count == 224 and originals == 98
    assert (
        max_fft < 1e-12
        and max_mhc < 5e-6
        and max_terms < 1e-12
        and max_mse < 1e-12
        and max_psnr < 1e-4
    )
    boards = [validate_board(b["receipt"]) for b in prepared["boards"]]
    assert sum(b["native_cells_exact"] for b in boards) == 28
    assert sum(len(b["source_triplets"]) for b in boards) == 20
    assert torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    result = {
        "status": "completed-independent-Torch-CPU-innovation-split-audit",
        "driver": ref(__file__),
        "plan": ref(root / "plan.json"),
        "scores": ref(root / "scores.json"),
        "original_array_fields_byte_exact": originals,
        "FP64_Torch_FFT_and_measured_sites_max_abs_error": max_fft,
        "frozen_FP32_MHC_replay_max_abs_error": max_mhc,
        "MSE_terms_checked": term_count,
        "MSE_terms_max_abs_error": max_terms,
        "metrics_checked": metric_count,
        "MSE_max_abs_error": max_mse,
        "PSNR_FP32_renderer_max_abs_error": max_psnr,
        "global_measured_CFA_contraction_all14": measured_contractions,
        "native_cells_exact": 28,
        "source_triplets_exact": 20,
        "CPU_RNG_unchanged": True,
        "CUDA_initialized": False,
        "scope": "Checks conditional GT-derived diagnostic arithmetic, not an inference method. Full-field measured-site contraction does not guarantee local, unmeasured-RGB or display fidelity. No GFX GT or production/training change.",
    }
    with (root / "array-audit.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(
        {
            k: v
            for k, v in result.items()
            if k not in ["global_measured_CFA_contraction_all14", "scope"]
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
