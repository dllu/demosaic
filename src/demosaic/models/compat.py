"""Historical constructors and checkpoint layouts, isolated from active execution."""


def build_component(kind, config=None):
    from demosaic.late_cfa_innovation_wave import LateCFAInnovationWaveDetail
    from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail
    from demosaic.late_scale_supported_cfa_wave import LateScaleSupportedCFAWaveDetail

    from .wave import compose_legacy

    constructors = {
        "pooled-wave": LatePooledPhaseWaveDetail,
        "cfa-wave": LateCFAInnovationWaveDetail,
        "scale-supported-cfa-wave": LateScaleSupportedCFAWaveDetail,
    }
    if kind not in constructors:
        raise ValueError(f"Unknown component kind: {kind}")
    # Retain exact seeded initialization; old classes are discarded after adoption.
    return compose_legacy(constructors[kind](**(config or {})))


def load_component(kind, checkpoint, *, config=None, device="cpu"):
    from demosaic.experiments.artifacts import reference
    from demosaic.experiments.checkpoints import load_torch

    from .wave import load_legacy_state_dict

    payload = load_torch(reference(checkpoint))
    model = build_component(kind, config if config is not None else payload["module_config"])
    load_legacy_state_dict(model, payload["state_dict"])
    return model.to(device), payload
