import json
from pathlib import Path

import numpy as np
import pytest
from lossless_native import fingerprint, load_native, ref, write_native


def baseline(tmp_path, array):
    p = tmp_path / "baseline.npy"
    np.save(p, array, allow_pickle=False)
    return ref(p)


@pytest.mark.parametrize("kind", ["random", "zeros", "signedzero", "subnormal"])
def test_exact_bits_for_lossless_planes_and_xor(tmp_path, kind):
    rng = np.random.default_rng(18505)
    x = rng.normal(size=(1, 3, 8, 11)).astype("<f4")
    if kind == "zeros":
        x.fill(0)
    if kind == "signedzero":
        x.ravel()[::2] = np.float32(-0.0)
    if kind == "subnormal":
        x = x * np.float32(1e-40)
    for name, prior in [("plain", None), ("xor", baseline(tmp_path, x * np.float32(0.9)))]:
        binding = write_native(tmp_path / f"{name}.json", x, baseline=prior)
        assert fingerprint(load_native(binding)) == fingerprint(x)


def test_addition_recipe_and_signed_zero_fallback(tmp_path):
    prior = np.zeros((1, 3, 8, 8), dtype="<f4")
    wave = np.full_like(prior, 0.001)
    base = baseline(tmp_path, prior)
    delta = write_native(tmp_path / "wave.json", wave)
    value = np.add(prior, wave, dtype=np.float32)
    output = write_native(tmp_path / "rgb.json", value, baseline=base, wave=delta)
    assert json.loads(Path(output["path"]).read_text())["encoding"] == "checked-f32-add"
    assert fingerprint(load_native(output)) == fingerprint(value)
    wave.fill(0)
    delta = write_native(tmp_path / "zero-wave.json", wave)
    desired = prior.copy()
    desired.ravel()[::2] = np.float32(-0.0)
    output = write_native(tmp_path / "signed.json", desired, baseline=base, wave=delta)
    assert json.loads(Path(output["path"]).read_text())["encoding"] == "xor-byteplanes-zlib"
    assert fingerprint(load_native(output)) == fingerprint(desired)


@pytest.mark.parametrize("part", ["manifest", "payload", "baseline"])
def test_tampering_is_rejected(tmp_path, part):
    x = np.arange(12, dtype="<f4").reshape(1, 3, 2, 2)
    base = baseline(tmp_path, x * 2)
    output = write_native(tmp_path / "rgb.json", x, baseline=base)
    metadata = json.loads(Path(output["path"]).read_text())
    p = output["path"] if part == "manifest" else metadata[part]["path"]
    with open(p, "ab") as stream:
        stream.write(b"changed")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_native(output)


def test_exclusive_publication_and_bad_contracts(tmp_path):
    x = np.zeros((1, 3, 2, 2), dtype="<f4")
    write_native(tmp_path / "x.json", x)
    with pytest.raises(ValueError):
        write_native(tmp_path / "x.json", x)
    with pytest.raises(ValueError):
        write_native(tmp_path / "double.json", x.astype("f8"))
    with pytest.raises(ValueError):
        write_native(tmp_path / "wave-only.json", x, wave=ref(tmp_path / "x.json"))
