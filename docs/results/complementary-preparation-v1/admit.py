"""Actual CUDA admission on training-only inputs; no optimizer update."""

from pathlib import Path

import numpy as np
import torch

from demosaic.cfa import color_indices, mosaic
from demosaic.experiments.artifacts import checked, reference, write_json
from demosaic.experiments.checkpoints import frozen_hash, trainable_parameters
from demosaic.experiments.cli import resolve_recipe
from demosaic.experiments.data.cache import CachedBatches
from demosaic.experiments.objectives.directional import objective
from demosaic.experiments.runtime import RuntimePolicy
from demosaic.experiments.training import initialize_model
from demosaic.models.compat import load_component
from demosaic.models.wave import legacy_state_dict

ROOT = Path(__file__).resolve().parent
recipe = Path('configs/experiments/complementary.json')
spec, _ = resolve_recipe(recipe)
policy = RuntimePolicy(**spec['runtime'])
policy.resources(ROOT)
policy.apply()
torch.ops.load_library(str(checked(spec['sampling_library'])))
_, arrays, parent, units = CachedBatches(spec['cache'], spec['pair_units']).load(7)
baseline, _ = load_component('scale-supported-cfa-wave', checked(spec['model']['initializer']), device='cuda')
baseline.eval().requires_grad_(False)
model = initialize_model(spec['model']).cuda().eval()
old, inherited = legacy_state_dict(baseline), legacy_state_dict(model.anchor)
assert len(old) == len(inherited) == 197
assert all(torch.equal(v, inherited[n]) for n, v in old.items())
frozen = frozen_hash(model)
channels = 0
counts = []
with torch.inference_mode():
    base = torch.from_numpy(parent[:1, :, :128, :128]).cuda()
    target = torch.from_numpy(arrays['target'][:1, :, :128, :128]).cuda()
    wb = torch.from_numpy(arrays['wb'][:1]).cuda()
    for pattern in ['RGGB', 'BGGR', 'GRBG', 'GBRG']:
        colors = color_indices(pattern, device='cuda')[None]
        rng = torch.Generator(device='cuda').manual_seed(202611160900 + channels)
        raw = mosaic(target, colors)
        raw = raw + torch.randn(raw.shape, generator=rng, device='cuda') * 0.001
        variance = torch.full_like(raw, 1e-6)
        expected = baseline(base, raw, variance, colors, wb)
        actual, aux = model(base, raw, variance, colors, wb, return_aux=True)
        assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))
        assert torch.equal(aux['anchor_output'], expected)
        channels += actual.numel()
        counts.append(dict(pattern=pattern, extra_valid=int(aux['cfa_evidence']['valid'].sum())))
        model.readout.gates.bias.fill_(0.3)
        expected = baseline(base, raw, variance * 0, colors, wb)
        actual = model(base, raw, variance * 0, colors, wb)
        assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))
        channels += actual.numel()
        model.readout.gates.bias.zero_()
del model, baseline
torch.cuda.empty_cache()
model = initialize_model(spec['model']).cuda().train()
batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
base = torch.from_numpy(parent).cuda()
output, aux = model(base, *(batch[k] for k in ['packed', 'variance', 'colors', 'wb']), return_aux=True)
loss, terms, _ = objective(output, aux['anchor_aux']['frozen_output'], batch, torch.from_numpy(units).cuda(), spec['domain_weights']['mesh'], mode=spec['training']['response'])
loss.backward()
trainable = trainable_parameters(model)
assert len(trainable) == 4 and sum(p.numel() for p in trainable.values()) == 643
assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in trainable.values())
assert max(float(p.grad.abs().max()) for p in trainable.values()) > 0
assert all(p.grad is None for p in model.anchor.parameters())
assert frozen == frozen_hash(model)
write_json(ROOT / 'result.json', dict(status='pass-full197-tensor-V200-anchor-all4CFA-zero-head-and-nonzero-head-ADC-real-gradient', script=reference(__file__), recipe=reference(recipe), initializer=spec['model']['initializer'], inherited_tensors_exact=197, trainable_tensors=4, trainable_parameters=643, exact_initial_or_ADC_RGB_channels=channels, engineering_noise_images=4, extra_proposals=counts, gradient_source=reference(checked(CachedBatches(spec['cache'], spec['pair_units']).rows[7]['arrays'])), maximum_gradient=max(float(p.grad.abs().max()) for p in trainable.values()), frozen_hash=frozen, peak_CUDA_bytes=torch.cuda.max_memory_allocated(), new_parent_DINO_forwards=0, optimizer_updates=0, probe_never_initializer=True, scope='Training-only engineering parity and gradient admission. Four synthetic Gaussian input corruptions are not performance data. Existing V200EMA197 tensors exact; no quality or strong-detail guarantee.'))
print('PASS all197 inherited tensors,', channels, 'exact noisy/ADC channels and full training-only gradient route.', flush=True)
