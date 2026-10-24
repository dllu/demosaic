import hashlib
import json
from types import SimpleNamespace

import evaluate_color_grid_cuda as color
import evaluate_texture_candidates as texture
import numpy as np
import pytest
import torch
import yaml

from demosaic import real_suite, suite
from demosaic.cfa import unpack
from demosaic.cli import parser


class SpatialBias(torch.nn.Module):
    def __init__(self, label='checkpoint'):
        super().__init__()
        self.calls = 0
        self.config = SimpleNamespace(to_dict=dict, variance_stabilization=False)
        self.receipt = {'label': label}

    def set_noise(self, *_args):
        pass

    def forward(self, packed, *_args):
        self.calls += 1
        value = unpack(packed).expand(-1, 3, -1, -1)
        ramp = torch.linspace(0, .01, value.shape[-1], device=value.device)
        return value + ramp[None, None, None]


def configure_models(monkeypatch, module):
    own, reference = SpatialBias().eval(), SpatialBias('reference-fixture').eval()
    state = {'step': 3, 'model_config': {}, 'config': {'run': 'unit'}}
    monkeypatch.setattr(module, 'load_checkpoint', lambda *_a, **_k: (own, state))
    monkeypatch.setattr(module, 'load_gaussian_prior', lambda *_a, **_k: reference)
    return own, reference


@pytest.mark.parametrize('policy,views', [('none', 1), ('dihedral8', 8)])
def test_photo_suite_averages_only_checkpoint_and_records_policy(tmp_path, monkeypatch, policy, views):
    torch.set_num_threads(2)
    own, reference = configure_models(monkeypatch, suite)
    checkpoint = tmp_path/'weights.pt'
    checkpoint.write_bytes(b'unit loader fixture')
    image = tmp_path/'source.npy'
    np.save(image, np.full((64, 64, 3), 16384, dtype=np.uint16))
    manifest = tmp_path/'manifest.jsonl'
    manifest.write_text(json.dumps({'id': 'unit-photo', 'split': 'val', 'cache': str(image)})+'\n')
    config = tmp_path/'protocol.yaml'
    config.write_text(yaml.safe_dump({'patterns': ['RGGB', 'GBRG'], 'seed': 42, 'border': 8,
        'white_balance': [1, 1, 1], 'camera_to_srgb': np.eye(3).tolist(),
        'conditions': [{'name': 'adc', 'shot': 0, 'read': 0, 'exposure': 1}]}))
    output = tmp_path/'photo'
    captured = []
    def capture(label, context, prediction, batch):
        if label.startswith('0:unit'):
            captured.append((context, prediction.clone(), {k: v.clone() for k, v in batch.items()}))
    suite.run_suite([checkpoint], manifest, output, config, patch_size=32, batch_size=1,
                    synthetic_count=0, device='cpu', precision='float32',
                    gaussian_reference=tmp_path/'reference', self_ensemble=policy,
                    prediction_callback=capture)
    assert own.calls == 2*views and reference.calls == 2
    assert len(captured) == 2
    assert {c['pattern'] for c, _, _ in captured} == {'RGGB', 'GBRG'}
    assert all(c['ids'] == ['unit-photo'] and c['seed'] == 42 for c, _, _ in captured)
    assert all(p.dtype == b['target'].dtype == torch.float32 and p.shape == b['target'].shape
               for _, p, b in captured)
    data = json.loads((output/'protocol.json').read_text())
    assert data['models'][0]['self_ensemble'] == policy
    assert data['models'][0]['model_views_per_tile'] == views
    assert data['learned_model_self_ensemble'] == policy
    rows = [json.loads(s) for s in (output/'per-image.jsonl').read_text().splitlines()]
    learned = [r for r in rows if r['model'].startswith('0:unit')]
    baseline = [r for r in rows if r['model'] == 'reference-fixture']
    assert all(r['model'].endswith(':dihedral8') for r in learned) == (views == 8)
    assert all(r['metrics']['gradient_mae'] > 1e-5 for r in baseline)
    if views == 8:
        assert all(r['metrics']['gradient_mae'] < 1e-7 for r in learned)
    else:
        assert all(r['metrics'] == b['metrics'] for r, b in zip(learned, baseline, strict=True))


@pytest.mark.parametrize('policy,views', [('none', 1), ('dihedral8', 8)])
def test_real_suite_preserves_reference_policy_and_measured_mask(tmp_path, monkeypatch, policy, views):
    own, reference = configure_models(monkeypatch, real_suite)
    checkpoint = tmp_path/'weights.pt'
    checkpoint.write_bytes(b'unit loader fixture')
    raw = np.full((96, 96), .18, dtype=np.float32)
    rgb = np.repeat(raw[None], 3, axis=0)
    mask = np.zeros_like(rgb, dtype=bool)
    for phase, channel in enumerate([0, 1, 1, 2]):
        y, x = divmod(phase, 2)
        mask[channel, y::2, x::2] = True
    crop = tmp_path/'crop.npz'
    np.savez(crop, raw=raw, reference_rgb=rgb, sensor_reference=rgb, sensor_mask=mask)
    case = {'scene': 'unit-scene', 'noisy': {'sha256': 'unit-pair'},
        'conditioning': {'shot': 0, 'read': 0},
        'metadata': {'pattern': 'RGGB', 'iso': 100, 'white_balance': [1, 1, 1],
                     'camera_to_srgb': np.eye(3).tolist()},
        'crops': [{'id': 'unit-crop', 'path': crop.name, 'xywh': [0, 0, 96, 96],
                   'sha256': hashlib.sha256(crop.read_bytes()).hexdigest()}]}
    manifest = tmp_path/'prepared.json'
    manifest.write_text(json.dumps({'cases': [case], 'split': 'unit', 'notes': 'unit-only fixture',
                                   'dataset_license': 'unit-only', 'attribution': 'unit fixture'}))
    output = tmp_path/'camera'
    captured = []
    def capture(label, context, prediction, batch):
        if label.startswith('0:unit'):
            captured.append((context, prediction.clone(), {k: v.clone() for k, v in batch.items()}))
    real_suite.evaluate_pairs([checkpoint], manifest, output, device='cpu', precision='float32',
        gaussian_reference=tmp_path/'reference', self_ensemble=policy, prediction_callback=capture)
    assert own.calls == views and reference.calls == 1
    assert len(captured) == 1 and captured[0][0]['ids'] == ['unit-crop']
    assert captured[0][0]['scene'] == 'unit-scene'
    assert torch.equal(captured[0][2]['sensor_mask'][0], torch.from_numpy(mask))
    assert torch.equal(captured[0][2]['reference_rgb'][0], torch.from_numpy(rgb))
    data = json.loads((output/'summary.json').read_text())
    assert data['models'][0]['self_ensemble'] == policy and data['models'][0]['model_views_per_tile'] == views
    rows = [json.loads(s) for s in (output/'per-crop.jsonl').read_text().splitlines()]
    own_row = next(r for r in rows if r['model'].startswith('0:unit'))
    reference_row = next(r for r in rows if r['model'] == 'reference-fixture')
    assert own_row['metrics']['reference_samples'] == reference_row['metrics']['reference_samples'] == 1024
    if views == 8:
        assert own_row['metrics']['ahd_gradient_mae'] < 1e-7
    else:
        assert own_row['metrics'] == reference_row['metrics']


@pytest.mark.parametrize('old_policy,new_policy,expected', [
    (None, None, 0), (None, 'dihedral8', None), ('dihedral8', None, None), ('dihedral8', 'dihedral8', 0)
])
def test_color_cache_cannot_reuse_another_policy(old_policy, new_policy, expected):
    old = {'kind': 'joint-checkpoint', 'sha256': 'a'*64, 'path': 'weights.pt',
           'compute_precision': 'float16, physicalFP32', 'memory_format': 'channels_last'}
    new = {'kind': 'joint-checkpoint', 'sha256': 'a'*64, 'path': 'weights.pt'}
    if old_policy is not None:
        old['self_ensemble'] = old_policy
    if new_policy is not None:
        new['self_ensemble'] = new_policy
    assert color.reuse_match(new, {'checkpoints': [old]}) == expected


@pytest.mark.parametrize('operator', ['photo', 'camera', 'texture', 'color'])
def test_invalid_policy_rejected_before_data_or_output(operator, tmp_path):
    output = tmp_path/'untouched'
    with pytest.raises(ValueError, match='policy'):
        if operator == 'photo':
            suite.run_suite([], 'missing', output, 'missing', self_ensemble='bad')
        elif operator == 'camera':
            real_suite.evaluate_pairs([], 'missing', output, self_ensemble='bad')
        elif operator == 'texture':
            texture.main([], output, self_ensemble='bad')
        else:
            color.evaluate_records('missing', 'missing', output, [], 'unused', self_ensemble='bad')
    assert not output.exists()


def test_quality_cli_exposes_policy_without_changing_default():
    args = ['quality', 'weights.pt', '--manifest', 'data.jsonl', '--output', 'output']
    assert parser().parse_args(args).self_ensemble == 'none'
    assert parser().parse_args(args+['--self-ensemble', 'dihedral8']).self_ensemble == 'dihedral8'


def test_texture_callback_retains_actual_targets_without_extra_forwards(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path/'configs').mkdir()
    (tmp_path/'configs/evaluation.yaml').write_text(yaml.safe_dump({
        'patterns': ['RGGB', 'BGGR', 'GRBG', 'GBRG'],
        'white_balance': [1, 1, 1], 'camera_to_srgb': np.eye(3).tolist(),
        'conditions': [{'name': name, 'shot': 0, 'read': 0, 'exposure': 1}
                       for name in texture.probe.CONDITIONS]}))
    own = SpatialBias().eval()
    state = {'step': 3, 'loaded_sha256': 'a'*64, 'config': {'run': 'unit'}}
    monkeypatch.setattr(texture, 'load_checkpoint', lambda *_a, **_k: (own, state))
    checkpoint = tmp_path/'fixture.pt'
    checkpoint.write_bytes(b'nonlearned fixture')
    captured = []
    def capture(label, context, prediction, batch):
        captured.append((context, tuple(prediction.shape), tuple(batch['target'].shape)))
    texture.main([checkpoint], tmp_path/'texture', device='cpu', precision='float32',
                 prediction_callback=capture)
    assert own.calls == len(captured) == 448//texture.probe.DRAWS
    assert {c['kind'] for c, _, _ in captured} == {'carrier', 'flat'}
    assert all(p == t == (texture.probe.DRAWS, 3, texture.probe.SIZE, texture.probe.SIZE)
               for _, p, t in captured)
