"""Describe retained GFX phase-patch means relative to the noise fit's support.

This compares observed patch means with accepted bin means, not with unknown
clean intensities. It neither refits noise nor changes conditioning or outputs.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main(report, output):
    source = json.loads(report.read_text())
    estimate = source["noise_estimate"]
    assert estimate["reliable"] is True and len(estimate["bins"]) >= 2
    lower, upper = (
        min(v["mean"] for v in estimate["bins"]),
        max(v["mean"] for v in estimate["bins"]),
    )
    records = [r for r in source["float_contexts"] if r["role"] == "noisy-packed"]
    assert len(records) == 4
    regions = []
    for record in records:
        path = report.parent / record["image"]
        assert sha(path) == record["sha256"]
        packed = np.load(path, allow_pickle=False)
        assert packed.dtype == np.float32 and packed.shape == (1, 4, 256, 256)
        assert np.isfinite(packed).all() and record["pattern"] == "RGGB"
        # Disjoint32x32 patches in each native CFA plane, no resampling.
        means = packed[0].astype(np.float64).reshape(4, 8, 32, 8, 32).mean(axis=(2, 4))
        checks = []
        for phase, name in enumerate(["R", "G1", "G2", "B"]):
            values = means[phase]
            checks.append(
                {
                    "phase": phase,
                    "color": name,
                    "patches": int(values.size),
                    "below_accepted_bin_mean_range": int((values < lower).sum()),
                    "above_accepted_bin_mean_range": int((values > upper).sum()),
                    "minimum_observed_mean": float(values.min()),
                    "median_observed_mean": float(np.median(values)),
                    "maximum_observed_mean": float(values.max()),
                }
            )
        regions.append(
            {
                "region": record["region"],
                "context_xywh": record["context_xywh"],
                "input": str(path),
                "input_sha256": sha(path),
                "patch_means": means.tolist(),
                "phase_counts": checks,
                "total_patches": int(means.size),
                "below": int((means < lower).sum()),
                "above": int((means > upper).sum()),
            }
        )
    result = {
        "status": "completed-retained-GFX-noise-fit-support-description",
        "report": str(report),
        "report_sha256": sha(report),
        "estimate": estimate,
        "accepted_bin_mean_range": [lower, upper],
        "conditioning": source["conditioning"],
        "regions": regions,
        "driver_sha256": sha(__file__),
        "scope": "Observed disjoint32x32 CFA-phase patch means versus accepted fit-bin mean range. Different filters/sampling from the fit; means are noisy and spatially dependent. Within-range does not certify calibration; outside-range does not establish an incorrect variance model. No reference, RAW decode, refit, noise/profile selection, restoration inference, output fitting or production change.",
    }
    output = writable_path(output)
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output.parent / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            {
                "output": str(output),
                "accepted_mean_range": [lower, upper],
                "regions": [
                    {
                        "name": r["region"]["name"],
                        "below": r["below"],
                        "above": r["above"],
                        "patches": r["total_patches"],
                    }
                    for r in regions
                ],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
