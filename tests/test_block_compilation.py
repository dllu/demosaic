import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices
from demosaic.inference import compile_restoration_blocks, load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig


def model():
    torch.manual_seed(51)
    net = JointDemosaic(
        ModelConfig(
            restoration_backbone="packed-isotropic",
            camera_conditioning=True,
            width=8,
            isotropic_groups=2,
            isotropic_blocks=1,
            isotropic_local_width=8,
        )
    ).eval()
    # Exercise learned spatial features instead of the initial zero RGB head.
    with torch.no_grad():
        net.packed_isotropic.head.weight.normal_(0, 0.02)
    return net


def inputs(height=17, width=25):
    raw = torch.linspace(-0.02, 0.9, 16 * height * width).reshape(4, 4, height, width)
    return (
        raw,
        raw.clamp_min(0) * 0.00256 + 0.0000262144,
        torch.stack([color_indices(pattern) for pattern in PATTERNS]),
    )


def test_inplace_compile_preserves_outputs_parameters_keys_and_portable_reload(tmp_path):
    net = model()
    before = {k: v.detach().clone() for k, v in net.restoration_state_dict().items()}
    identities = {name: id(value) for name, value in net.named_parameters()}
    with torch.inference_mode():
        expected = net(*inputs())
        assert compile_restoration_blocks(net, backend="eager") is net
        predicted = net(*inputs())
    assert predicted.dtype == torch.float32
    torch.testing.assert_close(expected, predicted, rtol=0, atol=0)
    assert identities == {name: id(value) for name, value in net.named_parameters()}
    after = net.restoration_state_dict()
    assert before.keys() == after.keys() and not any("_orig_mod" in key for key in after)
    for key, value in before.items():
        torch.testing.assert_close(value, after[key], rtol=0, atol=0)
    blocks = [
        net.packed_isotropic.local_blocks,
        *net.packed_isotropic.groups,
        net.packed_isotropic.decoder,
    ]
    calls = [block._compiled_call_impl for block in blocks]
    assert all(callable(call) for call in calls)
    compile_restoration_blocks(net, backend="eager")
    assert calls == [block._compiled_call_impl for block in blocks]
    assert all(
        module._compiled_call_impl is None
        for module in [
            net.packed_isotropic.stem,
            net.packed_isotropic.local_stem,
            net.packed_isotropic.up,
            net.packed_isotropic.head,
        ]
    )
    path = tmp_path / "portable.pt"
    torch.save({"model_config": net.config.to_dict(), "model": after}, path)
    reloaded, _ = load_checkpoint(path)
    reloaded.eval()
    assert not hasattr(reloaded, "_restoration_compilation_backend")
    with torch.inference_mode():
        torch.testing.assert_close(reloaded(*inputs()), predicted, rtol=0, atol=0)


def test_compiled_blocks_accept_another_odd_rectangle_without_moving_signal():
    net = model()
    with torch.inference_mode():
        expected = [net(*inputs(*shape)) for shape in [(17, 25), (21, 17)]]
        compile_restoration_blocks(net, backend="eager")
        for shape, reference in zip([(17, 25), (21, 17)], expected, strict=True):
            torch.testing.assert_close(net(*inputs(*shape)), reference, rtol=0, atol=0)


def test_inference_compile_rejects_training_unsupported_backbone_and_backend_change():
    net = model()
    net.train()
    with pytest.raises(ValueError, match="evaluation mode"):
        compile_restoration_blocks(net, backend="eager")
    legacy = JointDemosaic(
        ModelConfig(width=4, encoder_blocks=(), decoder_blocks=(), middle_blocks=0, attention=False)
    ).eval()
    with pytest.raises(ValueError, match="packed-isotropic"):
        compile_restoration_blocks(legacy, backend="eager")
    net.eval()
    for backend in ["", None, 3]:
        with pytest.raises(ValueError, match="named"):
            compile_restoration_blocks(net, backend=backend)
    compile_restoration_blocks(net, backend="eager")
    with pytest.raises(ValueError, match="different compilation backend"):
        compile_restoration_blocks(net, backend="inductor")
