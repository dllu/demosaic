import hashlib
import json
from pathlib import Path

import torch
import yaml

from demosaic.cfa import PATTERNS, color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import initialize_rgb_prior

torch.set_num_threads(2)
models, configs, lineages = [], [], []
for name in ["dino-anchored-native-fresh-b16-v44", "control-anchored-native-fresh-b16-v45"]:
    path = Path(f"configs/{name}.yaml")
    cfg = yaml.safe_load(path.read_text())
    configs.append(
        {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "config": cfg}
    )
    torch.manual_seed(cfg["seed"])
    model = JointDemosaic(ModelConfig(**cfg["model"])).cpu()
    lineages.append(initialize_rgb_prior(model, cfg["gaussian_initialization"]))
    assert all(p.device.type == "cpu" for p in model.parameters())
    models.append(model)

yes, no = (m.state_dict() for m in models)
assert set(no) == {k for k in yes if not k.startswith("context.")}
assert all(torch.equal(yes[k], no[k]) for k in no)
assert torch.count_nonzero(models[0].context.gate).item() == 0
assert all(not p.requires_grad for p in models[0].context.backbone.parameters())
assert models[1].context is None

cfg_a, cfg_b = (dict(c["config"]) for c in configs)
cfg_a.pop("run")
cfg_b.pop("run")
cfg_a["model"] = dict(cfg_a["model"])
cfg_b["model"] = dict(cfg_b["model"])
cfg_a["model"].pop("dino")
cfg_b["model"].pop("dino")
assert cfg_a == cfg_b
digest = hashlib.sha256()
for name, tensor in sorted(no.items()):
    digest.update(
        json.dumps(
            {"name": name, "dtype": str(tensor.dtype), "shape": list(tensor.shape)}, sort_keys=True
        ).encode()
        + b"\0"
    )
    digest.update(tensor.detach().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes())

raw = torch.rand(4, 4, 16, 16, generator=torch.Generator().manual_seed(48)) * 0.3
variance = raw * 0.001 + 1e-6
colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
with torch.no_grad():
    predictions = [model.eval().set_noise(0.001, 1e-6)(raw, variance, colors) for model in models]
assert all(torch.isfinite(p).all() and p.shape == (4, 3, 32, 32) for p in predictions)
assert torch.equal(*predictions)

result = {
    "status": "CPU initializer and all-CFA forward preflight only; GPU training pending",
    "configs": configs,
    "lineages": lineages,
    "all_common_tensors_exactly_equal": True,
    "common_state_tensors": len(no),
    "common_state_tensors_sha256": digest.hexdigest(),
    "zero_dino_gate": True,
    "frozen_dino_backbone": True,
    "cpu_fp32_four_cfa_initial_predictions_exactly_equal": True,
    "cpu_fp32_forward_shape": list(predictions[0].shape),
    "cpu_forward_conditioning": {"shot": 0.001, "read": 1e-6},
    "config_only_differences": ["run", "model.dino"],
    "parameters": [
        {
            "total": sum(p.numel() for p in m.parameters()),
            "trainable": sum(p.numel() for p in m.parameters() if p.requires_grad),
        }
        for m in models
    ],
    "source_files": {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path("src/demosaic").glob("*.py"))
    },
    "preflight_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "limitations": "No GPU training/forward/timing overlapped the owned V37/V39/V43 second gate. Initializer tensor equality alone does not demonstrate convergence, output equivalence under different arithmetic, DINO benefit or SOTA.",
}
Path("docs/results/fresh-dino-ablation-preflight.json").write_text(
    json.dumps(result, indent=2) + "\n"
)
print(
    json.dumps(
        {k: v for k, v in result.items() if k not in ["source_files", "configs", "lineages"]}
    ),
    flush=True,
)
