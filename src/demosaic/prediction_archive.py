"""Native FP32 predictions and exact supervision for later quality audits."""

import errno
import hashlib
import json
import os
import shutil
from pathlib import Path

import numpy as np

from .safety import writable_path


def _array(value):
    if hasattr(value, "detach"):
        value = value.detach().cpu().contiguous().numpy()
    result = np.asarray(value)
    if result.dtype.kind not in "buif" or not np.isfinite(result).all():
        raise ValueError("Archive arrays must be finite numeric values")
    return np.ascontiguousarray(result)


def fingerprint(value):
    """Describe logical values identically across contiguous/strided layouts."""
    array = _array(value)
    return {"shape": list(array.shape), "dtype": array.dtype.str,
            "sha256": hashlib.sha256(array.tobytes()).hexdigest()}


def _binding(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def _json(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))


class PredictionArchive:
    """One exclusive evaluation writer; targets are shared across models/CFAs.

    Records become visible only after both arrays are closed and checksummed.
    A failed evaluation leaves its completed records and partial work intact.
    Model execution, observations, metrics and image transforms stay with callers.
    """

    def __init__(self, output):
        self.output = writable_path(output).absolute()
        self.output.mkdir(parents=True, exist_ok=False)
        (self.output / "predictions").mkdir()
        (self.output / "supervision").mkdir()
        self.records = []
        self._models, self._targets, self._contexts = {}, {}, {}
        self.manifest = self.output / "records.jsonl"
        self.manifest.touch(exist_ok=False)

    def append(self, model, context, prediction, supervision, *, prediction_file=None):
        """Write one native B×3×H×W result, preserving FP32 and source identity."""
        model, context = json.loads(_json(model)), json.loads(_json(context))
        digest = model.get("sha256", "")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("A model requires its exact lowercase checkpoint SHA256")
        if not model.get("label") or model.get("self_ensemble") not in {"none", "dihedral8"}:
            raise ValueError("Declare a model label and inference policy")
        identity = digest, model["self_ensemble"]
        if identity in self._models and self._models[identity] != model:
            raise ValueError("Model metadata changed during evaluation")
        values = _array(prediction)
        if values.dtype != np.float32 or values.ndim != 4 or values.shape[1] != 3 or not all(values.shape):
            raise ValueError("Predictions must be native B×3×H×W float32")
        ids = context.get("ids")
        if not isinstance(ids, list) or len(ids) != len(values) or any(not isinstance(v, str) or not v for v in ids) or len(set(ids)) != len(ids):
            raise ValueError("One distinct source/draw ID is required per prediction")
        if not context.get("input_fingerprints"):
            raise ValueError("Retain the actual input fingerprints")
        target_arrays = {name: _array(value) for name, value in supervision.items()}
        if any(not name.isidentifier() for name in target_arrays):
            raise ValueError("Supervision keys must be identifiers")
        target = target_arrays.get("target", target_arrays.get("reference_rgb"))
        if target is None or target.dtype != np.float32 or target.shape != values.shape:
            raise ValueError("Retain an exact float32 RGB target/reference at native shape")
        for name, shape in [("wb", (len(values), 3)), ("matrix", (len(values), 3, 3))]:
            if name not in target_arrays or target_arrays[name].shape != shape:
                raise ValueError("Retain per-image white balance and camera matrix")
        context_key = _json(context)
        seen = self._contexts.setdefault(identity, set())
        if context_key in seen:
            raise ValueError("Duplicate model observation")
        descriptions = {name: fingerprint(value) for name, value in sorted(target_arrays.items())}
        target_key = hashlib.sha256(_json(descriptions).encode()).hexdigest()
        if target_key not in self._targets:
            path = self.output / "supervision" / (target_key+".npz")
            with path.open("xb") as stream:
                np.savez(stream, **target_arrays)
            path.chmod(0o444)
            self._targets[target_key] = _binding(path)
        index = len(self.records)
        path = self.output / "predictions" / f"batch-{index:06d}.npy"
        if prediction_file is None:
            with path.open("xb") as stream:
                np.save(stream, values, allow_pickle=False)
            path.chmod(0o444)
        else:
            source = Path(prediction_file)
            if fingerprint(np.load(source, allow_pickle=False)) != fingerprint(values):
                raise ValueError("Existing prediction differs from the evaluated values")
            # Share bytes on one filesystem. Across filesystems, preserve the
            # original NPY bytes in an exclusive copy without touching the source.
            try:
                os.link(source, path)
            except OSError as error:
                if error.errno != errno.EXDEV:
                    raise
                with source.open("rb") as original, path.open("xb") as destination:
                    shutil.copyfileobj(original, destination)
                path.chmod(0o444)
        row = {"schema": "demosaic-predictions-v1", "index": index, "model": model,
               "context": context, "prediction": _binding(path), "prediction_values": fingerprint(values),
               "supervision": self._targets[target_key], "supervision_values": descriptions}
        with self.manifest.open("a") as stream:
            stream.write(_json(row)+"\n")
        self.records.append(row)
        self._models[identity] = model
        seen.add(context_key)
        return row

    def verify_alignment(self):
        """Require identical observations and targets across methods, irrespective of order."""
        groups = {}
        for row in self.records:
            key = row["model"]["sha256"], row["model"]["self_ensemble"]
            groups.setdefault(key, {})[_json(row["context"])] = row["supervision_values"]
        if not groups:
            raise ValueError("No predictions retained")
        first = next(iter(groups.values()))
        if any(group != first for group in groups.values()):
            raise ValueError("Methods received different observations, inputs or supervision")
        return {"models": len(groups), "observations_per_model": len(first),
                "records": len(self.records), "unique_supervision_arrays": len(self._targets)}


def iter_predictions(manifest):
    """Stream checksummed predictions and exact targets; never run a model."""
    root = Path(manifest).absolute().parent
    for index, line in enumerate(Path(manifest).read_text().splitlines()):
        row = json.loads(line)
        if row["schema"] != "demosaic-predictions-v1" or row["index"] != index:
            raise ValueError("Unexpected archive schema or record sequence")
        for key in ["prediction", "supervision"]:
            path = Path(row[key]["path"])
            if not path.resolve().is_relative_to(root.resolve()) or _binding(path) != row[key]:
                raise ValueError("Archive file path/checksum mismatch")
        prediction = np.load(row["prediction"]["path"], allow_pickle=False)
        with np.load(row["supervision"]["path"], allow_pickle=False) as archive:
            targets = {k: archive[k].copy() for k in archive.files}
        if fingerprint(prediction) != row["prediction_values"] or {k: fingerprint(v) for k, v in targets.items()} != row["supervision_values"]:
            raise ValueError("Archive logical array metadata mismatch")
        yield row, prediction, targets
