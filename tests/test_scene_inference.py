"""Native coordinates, encoder reuse and deliberate context interventions."""

import pytest
import torch
from test_scene_restoration import Base

from demosaic.cfa import PATTERNS, pack
from demosaic.experiments.artifacts import reference
from demosaic.inference import restore_tiled
from demosaic.scene_inference import (
    SceneInferenceSession,
    load_scene_checkpoint,
    perturb_scene,
    restore_scene_tiled,
)
from demosaic.scene_restoration import WholeSceneRestorer


def session(mode="spatial", *, pattern="RGGB", context_policy="correct"):
    model = WholeSceneRestorer(Base(), mode=mode, adapter_width=4)
    raw = torch.rand(130, 194, generator=torch.Generator().manual_seed(53))
    return SceneInferenceSession(
        model,
        raw,
        PATTERNS[pattern],
        shot=0.001,
        read=1e-6,
        wb=[1.2, 1, 1.8],
        matrix=torch.eye(3),
        context_policy=context_policy,
    ), raw


@pytest.mark.parametrize("pattern", PATTERNS)
def test_native_queries_reuse_one_scene_and_preserve_actual_phase(pattern):
    current, raw = session(pattern=pattern)
    assert current.model.base.context.backbone.calls == 1
    boxes = [(0, 0, 32, 32), (162, 98, 32, 32)]
    prediction = current.predict_boxes(boxes, batch_size=1)
    assert current.model.base.context.backbone.calls == 3
    assert prediction.shape == (2, 3, 32, 32)
    for output, (x, y, w, h) in zip(prediction, boxes, strict=True):
        packed = pack(raw[None, None, y : y + h, x : x + w])
        expected = current.model.base(
            packed,
            packed.clamp_min(0) * 0.001 + 1e-6,
            current.colors[None],
            current.wb[None],
            current.matrix[None],
        )
        torch.testing.assert_close(output, expected[0], atol=0, rtol=0)
    # The caller cannot change the local observation after its context was encoded.
    raw.zero_()
    torch.testing.assert_close(current.predict_boxes(boxes), prediction, atol=0, rtol=0)


def test_tile_blend_matches_existing_inference_for_local_only_model():
    current, raw = session(mode="none")
    actual, stats = restore_scene_tiled(current, tile=32, overlap=8, batch_size=3)
    expected, _ = restore_tiled(
        current.model.base,
        raw,
        current.colors,
        shot=0.001,
        read=1e-6,
        wb=current.wb,
        matrix=current.matrix,
        tile=32,
        overlap=8,
        batch_size=3,
        device="cpu",
    )
    torch.testing.assert_close(actual, expected, atol=0, rtol=0)
    assert stats["scene_encoder_calls"] == 0
    assert stats["native_hw"] == [130, 194]


def test_scene_checkpoint_loads_its_bound_continuation_parent(tmp_path, monkeypatch):
    class Parent(Base):
        def restoration_state_dict(self):
            return {
                k: v for k, v in self.state_dict().items() if not k.startswith("context.backbone.")
            }

    parent_path = tmp_path / "continuation.pt"
    parent_path.write_bytes(b"continuation weights")
    bound_parent = reference(parent_path)
    model = WholeSceneRestorer(Parent(), mode="spatial", adapter_width=4)
    checkpoint = tmp_path / "scene.pt"
    torch.save(
        {
            "mode": "spatial",
            "adapter_width": 4,
            "base_parent": bound_parent,
            "ema": model.restoration_state_dict(),
        },
        checkpoint,
    )

    def load_parent(name, *, checkpoint, expected_sha256, device):
        assert name == "v120"
        assert checkpoint == parent_path and expected_sha256 == bound_parent["sha256"]
        return Parent().to(device), {"loaded_sha256": expected_sha256}

    monkeypatch.setattr("demosaic.models.load_model", load_parent)
    loaded, state = load_scene_checkpoint(checkpoint)
    assert state["loaded_weights"] == "ema"
    for key, value in loaded.restoration_state_dict().items():
        torch.testing.assert_close(value, model.restoration_state_dict()[key])

    parent_path.write_bytes(b"different continuation weights")
    with pytest.raises(ValueError, match="Artifact digest mismatch"):
        load_scene_checkpoint(checkpoint)


def test_feature_interventions_preserve_values_and_affect_delivered_rgb():
    current, _ = session()
    encoded = current.scene
    assert perturb_scene(encoded, "correct") is encoded
    shuffled = perturb_scene(encoded, "spatial-shuffled", seed=40)
    replay = perturb_scene(encoded, "spatial-shuffled", seed=40)
    for original, permuted, repeated in zip(
        encoded.features, shuffled.features, replay.features, strict=True
    ):
        torch.testing.assert_close(permuted, repeated, atol=0, rtol=0)
        torch.testing.assert_close(
            original.flatten(2).sort().values, permuted.flatten(2).sort().values, atol=0, rtol=0
        )
    with torch.no_grad():
        current.model.adapter.output.weight.fill_(0.15)
    boxes = [(8, 12, 32, 32)]
    correct = current.predict_boxes(boxes)
    current.scene = shuffled
    shuffled_rgb = current.predict_boxes(boxes)
    current.scene = perturb_scene(encoded, "masked")
    masked_rgb = current.predict_boxes(boxes)
    assert (correct - shuffled_rgb).abs().max() > 1e-4
    assert (correct - masked_rgb).abs().max() > 1e-4
    assert current.model.base.context.backbone.calls == 4  # one scene plus three local


@pytest.mark.parametrize(
    "box", [[1, 0, 32, 32], [-2, 0, 32, 32], [164, 0, 32, 32], [0, 0, 34, 32], [0, 0, 16, 32]]
)
def test_bad_native_query_rejected_before_local_forward(box):
    current, _ = session()
    with pytest.raises(ValueError, match="native boxes"):
        current.predict_boxes([box])
    assert current.model.base.context.backbone.calls == 1
