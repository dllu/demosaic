import importlib.util
from pathlib import Path

import torch

from demosaic.reference import RawNind

spec = importlib.util.spec_from_file_location(
    "report_raw_pair", Path(__file__).resolve().parents[1] / "scripts/report_raw_pair.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_gain_adapters_are_distinct_and_share_only_network_weights(tmp_path, monkeypatch):
    network = torch.nn.Identity()
    upstream = RawNind(network, gain_mode="cfa-ls")
    calls = []

    def load(directory, *, gain_mode, device):
        calls.append((directory, gain_mode, device))
        return upstream

    monkeypatch.setattr(module, "load_rawnind", load)
    (tmp_path / "utnet2-bayer.pt").write_bytes(b"Fixture weights")
    models, receipts = module.rawnind_comparators(tmp_path, ["cfa-ls", "cfa-channel", "cfa-ls"])
    assert len(calls) == 1 and len(models) == len(receipts) == 2
    first, second = (m[1] for m in models)
    assert first is not second and first.network is second.network
    assert first.gain_mode == "cfa-ls" and second.gain_mode == "cfa-channel"
    assert not first.training and not second.training
    second.input_scale = torch.ones(4) * .9
    assert first.input_scale is None
    assert [r["label"] for r in receipts] == ["RawNIND:CFA-LS", "RawNIND:CFA-channel"]
    assert receipts[0]["sha256"] == receipts[1]["sha256"]
