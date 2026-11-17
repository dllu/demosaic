"""Bind a fixed10k checkpoint review before any new prediction is measured."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, freeze_sources, read_json, reference, write_json
from demosaic.prediction_archive import fingerprint

repo = Path.cwd()
root = repo / '.cache/experiments/full-corpus-control10k-review-v1'
root.mkdir()
legacy_path = repo / '.cache/experiments/raw-spatial-endpoint-review-v3/queue-plan.json'
legacy = read_json(legacy_path)
observations = legacy['observations']
assert len(observations) == 102 and len({o['id'] for o in observations}) == 102
grid_path = Path('/mnt/external/demosaic/evaluation/prospective-color-grid-20261017-v1/plan.json')
grid = read_json(grid_path)
color_cases = [c for c in grid['cases'] if c['condition']['name'] == 'adc-only' and c['id'] in ['h030-s0.98-l0.90', 'gray-l0.18']]
assert len(color_cases) == 8
for case in color_cases:
    arrays = {'path': case['arrays'], 'sha256': case['sha256']}
    with np.load(checked(arrays), allow_pickle=False) as data:
        fingerprints = {k: fingerprint(data[k]) for k in ['packed', 'variance', 'colors', 'wb', 'matrix']}
    observations.append({'id': 'flat-' + case['id'] + '-' + case['pattern'], 'kind': 'color-spot-check',
                         'arrays': arrays, 'target': arrays, 'input_fingerprints': fingerprints,
                         'noise': case['condition'], 'source_id': case['id'], 'case_id': case['id'],
                         'pattern': case['pattern'], 'color_definition': case,
                         'output_shape': [1,3,256,256], 'ROI_xywh': [48,48,160,160], 'display_exposure': 1,
                         'reference_role': 'Exact constructed constant-color GT; diagnostic old V131 failure hue and a neutral flat, preselected independently of this10k model. Not the full588-color panel.'})
assert len(observations) == 110
training_root = repo / '.cache/experiments/full-corpus-scaling-v3'
training_plan_path = training_root / 'production-handoff-plan-v6.json'
training_plan = read_json(training_plan_path)
receipt_path = Path(training_plan['work']) / 'artifacts/train/control20k/step010000-receipt.json'
receipt = read_json(receipt_path)
assert receipt['global_step'] == 10000 and receipt['LR_horizon'] == 20000
models = {'V120': {'checkpoint': training_plan['parent'], 'step': 20000},
          'scale-control10k': {'checkpoint': receipt['checkpoint'], 'step': 10000,
                               'retained_progress': True, 'training_horizon': 20000}}
work, frozen = freeze_sources(repo, root, entries=['collect_full_corpus_checkpoint_review.py',
                            'report_checkpoint_pilot.py', 'analyze_retained_faint_detail.py'])
for relative in ['pyproject.toml', 'uv.lock', 'third_party/gaussian/Noise2VST-LICENSE',
                 'third_party/gaussian/KAIR-LICENSE', 'third_party/dinov3/LICENSE.md']:
    source, target = repo / relative, work / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    frozen[str(target)] = reference(target)['sha256']
bindings = [reference(legacy_path), reference(grid_path), reference(training_plan_path), reference(receipt_path)]
bindings += [v['checkpoint'] for v in models.values()]
bindings += [o['arrays'] for o in observations]
plan_path = root / 'plan.json'
write_json(plan_path, {'root': str(root), 'work': str(work), 'frozen_files': frozen, 'inputs': bindings,
           'collector': reference(work / 'scripts/collect_full_corpus_checkpoint_review.py'),
           'models': models, 'observations': observations, 'training_plan': reference(training_plan_path),
           'retained_checkpoint_receipt': reference(receipt_path), 'legacy_inputs_plan': reference(legacy_path),
           'DINO_sha256': training_plan['DINO_sha256'], 'CPU_affinity': [6,7], 'CPU_threads': 2,
           'maximum_seconds': 21600, 'planned_root_calls': 220, 'planned_DINO_executions': 110,
           'scope': 'Prospectively fixed10k-of20k scaling review:96 retained material observations (ordinary16,shadow64,faint-ADC16),4 main GFX and2 cab-profile contexts,8 diagnostic ADC flat colors. All110 physical observations reused unchanged, no new RAW/noise. Fresh matched CPU parent and candidate, exact EMA, shared checked identical frozen DINO calls. Protected media remain excluded/read-only. This is not a completed20k/100k endpoint, full427/camera panel, or the full588-color validation. Both GFX families/native exact-GT/approximate references and faithful-detail/quiet/colour diagnostics required; no quality-based stopping or checkpoint selection.'})
env = dict(os.environ, PYTHONPATH=str(work/'src')+':'+str(work/'scripts'),
           OMP_NUM_THREADS='2', OPENBLAS_NUM_THREADS='2', MKL_NUM_THREADS='2', PYTHONUNBUFFERED='1')
command = [sys.executable, str(work/'scripts/collect_full_corpus_checkpoint_review.py'), str(plan_path)]
with (root/'collector.log').open('x') as log:
    process = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
import psutil
write_json(root/'launch.json', {'pid': process.pid, 'create_time': psutil.Process(process.pid).create_time(),
           'command': command, 'plan': reference(plan_path), 'preparer': reference(__file__),
           'scope': 'One declared CPU-only review; existing training and full primary evaluation untouched. No automatic retry.'})
print('Launched fixed10k review', process.pid, psutil.Process(process.pid).create_time(), '110 observations/220 roots,0 new GPU/RAW/noise/optimizer')
