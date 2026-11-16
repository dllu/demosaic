"""Small, explicit catalogue; listing presets never loads weights or Torch."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelPreset:
    name: str
    kind: str
    role: str
    report: str
    checkpoint: str | None = None
    sha256: str | None = None


_PRESETS = (
    ModelPreset(
        "v120",
        "joint",
        "general recommendation",
        "docs/v120-v121-primary.md",
        "/mnt/external/demosaic/models/v120-final20000.pt",
        "a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb",
    ),
    ModelPreset(
        "v114", "joint", "Tiny alternative; lower tested ADC maximum", "docs/v114-v115-quality.md"
    ),
    ModelPreset(
        "v131",
        "joint",
        "experimental photo/faint gains; unseen-camera and ADC-color costs",
        "docs/v131-broad-primary.md",
        sha256="4d78e6302f6e72d68acb03fe58eb7106763b8129ccb059747ef5d2cfbd3ec1e1",
    ),
    ModelPreset(
        "v131-adc-malvar",
        "joint",
        "experimental fixed ADC repair; positive-noise V131 unchanged",
        "docs/v131-adc-projection.md",
        sha256="6b1851e85933b56001ee1100e6ef0083173f3949849c1429894534a5caf2708e",
    ),
    ModelPreset(
        "v187",
        "pooled-wave",
        "experimental quieter wave option",
        "docs/pooled-phase-wave-comparison.md",
    ),
    ModelPreset(
        "v195",
        "pooled-wave",
        "experimental stronger-response anchor",
        "docs/directional-response-comparison.md",
    ),
    ModelPreset(
        "v198",
        "cfa-wave",
        "experimental stronger detail; building color artifacts",
        "docs/cfa-innovation-wave-comparison.md",
    ),
    ModelPreset(
        "v200",
        "scale-supported-cfa-wave",
        "experimental small quiet/flat gains",
        "docs/scale-supported-cfa-wave-comparison.md",
    ),
    ModelPreset(
        "competing",
        "orientation-balanced-cfa-wave",
        "experimental local directional gain; lower aggregate mesh response",
        "docs/competing-orientation-comparison.md",
    ),
    ModelPreset(
        "complementary",
        "complementary-cfa-wave",
        "experimental lower-noise weak-response gain; high-noise flat costs",
        "docs/complementary-edge-response.md",
    ),
)


def model_presets():
    return [asdict(preset) for preset in _PRESETS]


def load_model(name="v120", *, checkpoint=None, expected_sha256=None, device="cpu"):
    from demosaic.experiments.artifacts import checked, reference

    preset = next((p for p in _PRESETS if p.name == name.lower()), None)
    if preset is None:
        raise ValueError(f"Unknown model preset: {name}")
    path = checkpoint or preset.checkpoint
    if path is None:
        raise ValueError(f"Specify the checkpoint for {name}; see {preset.report}")
    binding = reference(path)
    expected = expected_sha256 or preset.sha256
    if expected is not None and binding["sha256"] != expected:
        raise ValueError(f"Checkpoint does not match {name}'s declared SHA256")
    checked(binding)
    if preset.kind == "joint":
        from demosaic.inference import load_checkpoint

        model, payload = load_checkpoint(path, device)
        if payload["loaded_sha256"] != binding["sha256"]:
            raise ValueError("Checkpoint changed during loading")
        return model, payload
    from .compat import load_component

    return load_component(preset.kind, path, device=device)
