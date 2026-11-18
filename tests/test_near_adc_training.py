"""The bridge augments only simulated ADC observations and keeps paired inputs exact."""

from types import SimpleNamespace

import pytest
import torch

from demosaic.near_adc_training import bridge_fraction, require_resume_near_adc_bridge
from demosaic.train import prepare_training_batch


@pytest.mark.parametrize("domain,step", [("commons", 23), ("native", 24)])
def test_bridge_resimulates_only_adc_slots_without_moving_original_rng(domain, step):
    rgb = torch.linspace(0.04, 0.2, 16 * 3 * 12 * 12).reshape(16, 3, 12, 12)
    clean = (
        {"rgb": rgb}
        if domain == "commons"
        else {"camera_rgb": rgb, "wb": torch.ones(16, 3), "matrix": torch.eye(3).repeat(16, 1, 1)}
    )
    model = SimpleNamespace(config=SimpleNamespace(physical_fp32=True))
    config = {
        "data_seed_per_step": True,
        "noise_free_fraction": 0.5,
        "camera_supervision": "sensor-valid-v1",
        "reconstruct_highlights": True,
        "preserve_negative_read_noise": True,
    }

    def prepare(options):
        return prepare_training_batch(
            step, domain, clean, model=model, device="cpu", config=options, seed=171
        )

    rng = torch.random.get_rng_state()
    control = prepare(config)
    bridge = prepare({**config, "near_adc_bridge_fraction": 0.5})
    repeat = prepare({**config, "near_adc_bridge_fraction": 0.5})
    assert torch.equal(rng, torch.random.get_rng_state())
    assert control.keys() == bridge.keys() == repeat.keys()
    assert all(torch.equal(t, repeat[k]) for k, t in bridge.items())
    selected = (control["shot"] != bridge["shot"]).flatten()
    assert 0 < int(selected.sum()) < int((control["shot"] == 0).sum())
    assert (control["shot"][selected] == 0).all() and (control["read"][selected] == 0).all()
    assert (bridge["shot"][selected] > 0).all() and (bridge["read"][selected] > 0).all()
    assert not torch.equal(control["packed"][selected], bridge["packed"][selected])
    for key, value in control.items():
        if key in {"packed", "variance", "read", "shot"}:
            assert torch.equal(value[~selected], bridge[key][~selected])
        else:
            assert torch.equal(value, bridge[key])
    torch.testing.assert_close(
        bridge["variance"],
        bridge["packed"].clamp_min(0) * bridge["shot"] + bridge["read"],
        rtol=0,
        atol=0,
    )


def test_paired_training_is_untouched_and_old_config_resumes():
    clean = {"packed": torch.rand(2, 4, 8, 8), "sensor_mask": torch.ones(2, 3, 16, 16)}
    paired = prepare_training_batch(
        1,
        "paired",
        clean,
        model=None,
        device="cpu",
        config={"near_adc_bridge_fraction": 0.5},
        seed=171,
    )
    assert all(paired[k] is value for k, value in clean.items())
    require_resume_near_adc_bridge({}, {"near_adc_bridge_fraction": 0})
    with pytest.raises(ValueError, match="Resume near-ADC bridge fraction"):
        require_resume_near_adc_bridge({}, {"near_adc_bridge_fraction": 0.5})


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf"), True, "0.5"])
def test_invalid_bridge_fraction(value):
    with pytest.raises(ValueError, match="Near-ADC bridge fraction"):
        bridge_fraction({"near_adc_bridge_fraction": value})
