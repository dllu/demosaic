"""Prepare and execute seven discarded production-size RAW-head warmup updates."""

import argparse
import gc
import hashlib
import json
from pathlib import Path

import psutil
import torch
import yaml

REPO = Path('/home/dllu/proj/demosaic')
BASE = Path('/mnt/external/demosaic')
CPU = BASE/'benchmarks/raw-kernel-warmup-CPU-preflight-v1/receipt.json'
GPU = BASE/'benchmarks/raw-kernel-CUDA-preflight-v1/receipt.json'
REVIEW = REPO/'docs/results/long-commons-v63-v64-first4k-review.json'
RECIPE = REPO/'configs/dino-convnext-raw-kernel-warmup-b16-v65.yaml'
SOURCE = '32a330278824bb0b06b27a7b00439d10a3d853966ee3864ceb96a99ff08ae1c0'


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def prepare(out):
    assert not torch.cuda.is_initialized() and not out.exists()
    proof = read(CPU)
    assert proof['status'] == 'completed-CPU-RAW-head-warmup-preflight'
    assert read(GPU)['status'].startswith('completed-discarded-B16-native256-CUDA')
    assert read(REVIEW)['review_complete'] is True
    cfg = yaml.safe_load(RECIPE.read_text())
    assert cfg['steps'] == 1000 and cfg['raw_kernel_only'] is True
    assert (cfg['batch_size'], cfg['patch_size'], cfg['precision']) == (16, 256, 'bfloat16')
    parent = Path(proof['parent']['path'])
    assert sha(parent) == proof['parent']['sha256']
    paths = [CPU, GPU, REVIEW, RECIPE, parent, Path(cfg['validation_protocol'])]
    paths += [Path(cfg[k]) for k in ['manifest', 'validation_manifest', 'raw_clean_manifest', 'paired_manifest']]
    inputs = {str(p): sha(p) for p in paths}
    out.mkdir(parents=True)
    project = out/'candidate'
    package = project/'src/demosaic'
    package.mkdir(parents=True)
    for source, digest in proof['source_files'].items():
        assert sha(source) == digest
        (package/Path(source).name).write_bytes(Path(source).read_bytes())
    for name in ['pyproject.toml', 'uv.lock', 'third_party/gaussian/Noise2VST-LICENSE', 'third_party/gaussian/KAIR-LICENSE', 'third_party/dinov3/LICENSE.md']:
        target = project/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO/name).read_bytes())
    tools = out/'tools'
    tools.mkdir()
    for p in (REPO/'scripts').glob('*.py'):
        (tools/p.name).write_bytes(p.read_bytes())
    cfg.update(run=str(out/'actual-B16'), workers=0, raw_clean_workers=0,
               paired_workers=0, flat_fraction=0, synthetic_fraction=0,
               validation_images=2, val_batches=1, checkpoint_every=7, log_every=1)
    fixture = out/'fixture.yaml'
    fixture.write_text(yaml.safe_dump(cfg, sort_keys=False))
    files = {str(p): sha(p) for p in out.rglob('*') if p.is_file()}
    plan = {'status': 'prepared-CPU-only-warmup-CUDA-fixture', 'package': str(project/'src'),
            'operator': str(tools/Path(__file__).name), 'fixture': str(fixture),
            'parent': str(parent), 'parent_sha256': sha(parent), 'source_bundle_sha256': SOURCE,
            'inputs': inputs, 'archived_files': files, 'fixture_updates': 7,
            'scope': 'Seven discarded B16/native256/BF16 updates; forced real Commons/workers0/val2. No production training or quality result.'}
    (out/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    print(json.dumps({'plan': str(out/'plan.json'), 'CUDA_initialized': False}), flush=True)


def execute(out):
    from preflight_flat_palette_cuda import portable_predictions
    from preflight_raw_kernel_cuda import call, initialized_parent, photo

    from demosaic import train as module
    from demosaic.inference import load_checkpoint
    from demosaic.train import make_optimizer, train

    plan = read(out/'plan.json')
    assert Path(module.__file__).resolve() == Path(plan['package'])/'demosaic/train.py'
    assert not torch.cuda.is_initialized() and not (out/'receipt.json').exists()
    for p, digest in (plan['inputs'] | plan['archived_files']).items():
        assert sha(p) == digest, p
    assert psutil.virtual_memory().available/1e9 > 32
    assert psutil.disk_usage(BASE).free/1024**3 > 512
    cfg = yaml.safe_load(Path(plan['fixture']).read_text())
    assert not Path(cfg['run']).exists()
    torch.set_num_threads(4)
    initial = initialized_parent(cfg)
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    cp = train(plan['fixture'], initialize=plan['parent'], stop_after=7)
    state = torch.load(cp, map_location='cpu', weights_only=True, mmap=True)
    parent = torch.load(plan['parent'], map_location='cpu', weights_only=True, mmap=True)
    assert state['step'] == 7 and state['config']['steps'] == 1000
    assert state['config']['source_sha256'] == SOURCE and state['config']['raw_kernel_only'] is True
    assert len(state['model']) == len(state['ema']) == 93 and len(state['optimizer']['state']) == 2
    assert {int(v['step']) for v in state['optimizer']['state'].values()} == {7}
    assert all(torch.isfinite(v).all() for k in ['model', 'ema'] for v in state[k].values())
    assert all(torch.isfinite(v).all() for item in state['optimizer']['state'].values() for v in item.values() if isinstance(v, torch.Tensor))
    for name, value in parent['ema'].items():
        assert torch.equal(state['model'][name], value) and torch.equal(state['ema'][name], value), name
    head = [n for n in state['model'] if n.startswith('pretrained_rgb.raw_kernel.')]
    assert len(head) == 2 and all(torch.count_nonzero(state['model'][n]) > 0 for n in head)
    rows = [r for line in (Path(cfg['run'])/'metrics.jsonl').read_text().splitlines() if (r := json.loads(line)).get('event') == 'train']
    assert [r['step'] for r in rows] == list(range(1, 8))
    assert {r['domain'] for r in rows} == {'synthetic', 'paired-RAW', 'native-RAW-synthetic'}
    portable = portable_predictions(cp, state, cfg)
    model, _ = load_checkpoint(cp, 'cuda')
    model.to(memory_format=torch.channels_last).eval()
    optimizer = make_optimizer(model, state['config'])
    optimizer.load_state_dict(state['optimizer'])
    assert sorted(n for n,p in model.named_parameters() if p.requires_grad) == sorted(head)
    assert sum(p.numel() for p in model.parameters() if p.requires_grad) == 22032
    _, batch = photo(0, 'cuda')
    loss = call(model, batch, 'bfloat16').square().mean()
    loss.backward()
    gradients = {}
    for name, parameter in model.named_parameters():
        if name in head:
            assert parameter.grad is not None and torch.isfinite(parameter.grad).all() and parameter.grad.abs().sum() > 0
            gradients[name] = float(parameter.grad.norm())
        else:
            assert parameter.grad is None and not parameter.requires_grad
    for p, digest in (plan['inputs'] | plan['archived_files']).items():
        assert sha(p) == digest
    result = {'status': 'completed-discarded-B16-native256-CUDA-head-only-warmup-checks',
              'plan': str(out/'plan.json'), 'plan_sha256': sha(out/'plan.json'),
              'checkpoint': {'path': str(cp), 'sha256': sha(cp)},
              'source_bundle_sha256': SOURCE, 'initialization': initial,
              'all91_existing_model_and_EMA_tensors_exact_to_parent': True,
              'finite_model_tensors': 93, 'finite_EMA_tensors': 93, 'finite_AdamW_states': 2,
              'training_observations': rows, 'portable_FP16_photos_and_optimizer_RNG_restore': portable,
              'B1_native256_BF16_head_gradient_norms': gradients,
              'all_other_parameters_frozen_and_gradient_free': True,
              'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
              'driver_sha256': sha(__file__),
              'scope': 'Discarded seven-update engineering fixture only. Actual head-only optimizer/scope/EMA/gradient and physical FP32 head under BF16. No convergence, noisy-field unbiasedness, production throughput, deterministic CUDA restart or restoration-quality claim.'}
    (out/'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'receipt': str(out/'receipt.json'), 'peak_cuda_allocated_bytes': result['peak_cuda_allocated_bytes']}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare-only', action='store_true')
    mode.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if args.prepare_only:
        prepare(args.output)
    else:
        execute(args.output)
