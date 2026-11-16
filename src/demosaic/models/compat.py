"""Historical constructors and checkpoint layouts, isolated from active execution."""


def build_component(kind, config=None):
    from demosaic.late_cfa_innovation_wave import LateCFAInnovationWaveDetail
    from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail
    from demosaic.late_scale_supported_cfa_wave import LateScaleSupportedCFAWaveDetail

    from .wave import compose_legacy

    config = dict(config or {})
    complementary = kind == "complementary-cfa-wave"
    competing = kind == "orientation-balanced-cfa-wave" or complementary
    family_degrees = config.pop("family_degrees", 20.0) if competing else None
    if competing:
        import math

        if (
            type(family_degrees) not in (int, float)
            or not math.isfinite(family_degrees)
            or not 0 < family_degrees < 45
        ):
            raise ValueError("Expected an angular family radius between0 and45degrees")
    constructors = {
        "pooled-wave": LatePooledPhaseWaveDetail,
        "cfa-wave": LateCFAInnovationWaveDetail,
        "scale-supported-cfa-wave": LateScaleSupportedCFAWaveDetail,
        "orientation-balanced-cfa-wave": LateScaleSupportedCFAWaveDetail,
        "complementary-cfa-wave": LateScaleSupportedCFAWaveDetail,
    }
    if kind not in constructors:
        raise ValueError(f"Unknown component kind: {kind}")
    # Retain exact seeded initialization; old classes are discarded after adoption.
    module = compose_legacy(constructors[kind](**config))
    if complementary:
        import copy

        from .wave import ComplementaryWaveStage

        module = ComplementaryWaveStage(
            module, copy.deepcopy(module.readout), family_degrees=family_degrees
        )
    elif competing:
        from functools import partial

        from demosaic.competing_phase import competing_phase_bins

        module.selector = partial(competing_phase_bins, family_degrees=family_degrees)
    return module


def load_component(kind, checkpoint, *, config=None, device="cpu"):
    from demosaic.experiments.artifacts import reference
    from demosaic.experiments.checkpoints import load_torch

    from .wave import load_legacy_state_dict

    payload = load_torch(reference(checkpoint))
    model = build_component(kind, config if config is not None else payload["module_config"])
    load_legacy_state_dict(model, payload["state_dict"])
    return model.to(device), payload
