"""Exact FP32 native arrays with checked dependencies and lossless byte planes.

New outputs only: a checked baseline-plus-wave recipe avoids storing redundant
RGB bits when NumPy FP32 addition reproduces every original bit. Otherwise use
byte-plane zlib, optionally after XOR with an immutable baseline. No quantizing.
"""

import hashlib
import json
import os
import zlib
from pathlib import Path

import numpy as np


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def fingerprint(array):
    array = np.ascontiguousarray(array)
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
    }


def checked(binding):
    if ref(binding["path"]) != binding:
        raise ValueError("Native dependency file digest mismatch")
    return Path(binding["path"])


def publish_exclusive(path, data):
    path = Path(path)
    temporary = path.with_name("." + path.name + ".writing")
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)  # Atomic publication; never replace existing output.
    temporary.unlink()


def load_native(binding):
    path = checked(binding) if isinstance(binding, dict) else Path(binding)
    if path.suffix == ".npy":
        return np.load(path, allow_pickle=False)
    metadata = json.loads(path.read_text())
    if metadata["format"] != "exact-native-f32-v1":
        raise ValueError("Unknown native format")
    expected = metadata["values"]
    shape = tuple(expected["shape"])
    if expected["dtype"] != "<f4" or any(type(n) is not int or n < 1 for n in shape):
        raise ValueError("Expected little-endian FP32 native array")
    if metadata["encoding"] == "checked-f32-add":
        baseline = load_native(metadata["baseline"])
        wave = load_native(metadata["wave"])
        if baseline.shape != shape or wave.shape != shape:
            raise ValueError("Addition operand shape mismatch")
        value = np.add(baseline, wave, dtype=np.float32)
    elif metadata["encoding"] in ["byteplanes-zlib", "xor-byteplanes-zlib"]:
        compressed = checked(metadata["payload"]).read_bytes()
        raw = zlib.decompress(compressed)
        count = int(np.prod(shape))
        if len(raw) != count * 4:
            raise ValueError("Native payload length mismatch")
        bits = np.frombuffer(raw, dtype=np.uint8).reshape(4, count).T.copy()
        bits = bits.reshape(-1).view("<u4").reshape(shape)
        if metadata["encoding"] == "xor-byteplanes-zlib":
            baseline = load_native(metadata["baseline"])
            if baseline.shape != shape or baseline.dtype != np.dtype("<f4"):
                raise ValueError("XOR baseline contract mismatch")
            bits = np.bitwise_xor(bits, baseline.view("<u4"))
        value = bits.view("<f4")
    else:
        raise ValueError("Unknown native encoding")
    if fingerprint(value) != expected:
        raise ValueError("Decoded native array bit digest mismatch")
    return value


def write_native(path, array, *, baseline=None, wave=None):
    """Publish one exact array; wave is a binding to an already closed array."""
    path = Path(path)
    if path.suffix != ".json" or path.exists():
        raise ValueError("Expected a new JSON native manifest")
    value = np.ascontiguousarray(array)
    if value.dtype != np.dtype("<f4") or not np.isfinite(value).all():
        raise ValueError("Expected finite little-endian FP32 native values")
    metadata = {"format": "exact-native-f32-v1", "values": fingerprint(value)}
    prior = load_native(baseline) if baseline is not None else None
    if prior is not None and (prior.shape != value.shape or prior.dtype != value.dtype):
        raise ValueError("Baseline contract mismatch")
    if wave is not None:
        if prior is None:
            raise ValueError("An addition recipe requires an immutable baseline")
        delta = load_native(wave)
        if delta.shape != value.shape or delta.dtype != value.dtype:
            raise ValueError("Wave contract mismatch")
        reproduced = np.add(prior, delta, dtype=np.float32)
        if fingerprint(reproduced) == metadata["values"]:
            metadata.update(encoding="checked-f32-add", baseline=baseline, wave=wave)
    if "encoding" not in metadata:
        bits = value.view("<u4")
        if prior is not None:
            bits = np.bitwise_xor(bits, prior.view("<u4"))
        planes = bits.view(np.uint8).reshape(-1, 4).T.copy().tobytes()
        payload = path.with_suffix(".zlib")
        publish_exclusive(payload, zlib.compress(planes, level=6))
        metadata.update(
            encoding="byteplanes-zlib" if prior is None else "xor-byteplanes-zlib",
            payload=ref(payload),
        )
        if prior is not None:
            metadata["baseline"] = baseline
    publish_exclusive(path, (json.dumps(metadata, indent=2, allow_nan=False) + "\n").encode())
    binding = ref(path)
    if fingerprint(load_native(binding)) != metadata["values"]:
        raise ValueError("Published native round trip failed")
    return binding
