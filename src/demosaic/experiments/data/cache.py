"""Stream checked observations and cached parent predictions without resampling."""

import numpy as np

from demosaic.prediction_archive import fingerprint

from ..artifacts import checked, read_json


class CachedBatches:
    def __init__(self, cache, pair_units):
        self.rows = read_json(checked(cache))["batches"]
        self.units = read_json(checked(pair_units))["rows"]
        if len(self.rows) != len(self.units) or not self.rows:
            raise ValueError("Cache and unit schedule must have the same nonzero length")
        for step, (row, unit) in enumerate(zip(self.rows, self.units, strict=True), 1):
            if row["step"] != step or unit["step"] != step or unit["batch"] != row["arrays"]:
                raise ValueError(f"Misaligned cache/unit schedule at row {step}")

    def __len__(self):
        return len(self.rows)

    def load(self, index):
        row, unit = self.rows[index], self.units[index]
        with np.load(checked(row["arrays"]), allow_pickle=False) as archive:
            arrays = dict(archive)
        parent = np.load(checked(row["parent"]), allow_pickle=False)
        if {k: fingerprint(v) for k, v in arrays.items()} != row["inputs"]:
            raise ValueError(f"Input values differ at row {row['step']}")
        if fingerprint(parent) != row["parent_values"]:
            raise ValueError(f"Parent values differ at row {row['step']}")
        values = np.asarray(unit["candidate_units_FP32"], dtype=np.float32).reshape(-1, 1, 1, 1)
        if len(values) != len(arrays["pair_indices"]) or not np.isfinite(values).all():
            raise ValueError("Invalid per-pair units")
        if (values <= 0).any():
            raise ValueError("Per-pair units must be positive")
        return row, arrays, parent, values

    def audit(self):
        noisy = images = pairs = 0
        for index in range(len(self)):
            _, arrays, parent, units = self.load(index)
            if parent.shape != arrays["target"].shape or not np.isfinite(parent).all():
                raise ValueError("Invalid cached parent shape/values")
            active = bool(np.any(arrays["variance"] > 0))
            noisy += active
            images += len(parent) if active else 0
            pairs += len(units) if active else 0
        return {"rows": len(self), "noisy_updates": noisy, "ADC_skips": len(self) - noisy,
                "training_images": images, "coupled_pairs": pairs}
