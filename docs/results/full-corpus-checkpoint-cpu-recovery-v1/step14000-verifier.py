"""Bind the first actual production checkpoint after CPU snapshot recovery."""
import os
import shutil
from pathlib import Path
from datetime import datetime,timezone
import psutil
import torch
from demosaic.experiments.artifacts import read_json,reference,write_json

torch.set_num_threads(2)
repo=Path.cwd();root=repo/'.cache/experiments/full-corpus-scaling-v3';recovery=root/'checkpoint-recovery-v7'
launch=read_json(root/'production-handoff-v7/00-scale-control20k-launch.json');p=psutil.Process(launch['pid']);assert p.create_time()==launch['create_time']
run=recovery/'work/artifacts/train/control20k';out=recovery/'post-repair-step14000-v1';out.mkdir()
os.link(run/'last.pt',out/'step014000.pt')
state=torch.load(out/'step014000.pt',map_location='cpu',weights_only=True)
assert state['step']==14000 and len(state['model'])==len(state['ema'])==91 and len(state['optimizer']['state'])==89
assert all(v['step']==14000 for v in state['optimizer']['state'].values())
assert all(torch.isfinite(v).all()for k in ['model','ema']for v in state[k].values())
assert all(torch.isfinite(t).all()for v in state['optimizer']['state'].values()for t in v.values()if isinstance(t,torch.Tensor))
assert state['config']['steps']==20000 and state['config']['batch_size']==16
assert state['python_rng']and state['cuda_rng']and state['torch_rng'].numel()
def cpu(v):
    if isinstance(v,torch.Tensor):assert v.device.type=='cpu'
    elif isinstance(v,dict):
        for x in v.values():cpu(x)
    elif isinstance(v,(tuple,list)):
        for x in v:cpu(x)
cpu(state)
log=root/'production-handoff-v7/00-scale-control20k.log';snapshot=out/'log-snapshot.log';snapshot.open('xb').write(log.read_bytes())
events=[__import__('json').loads(l)for l in snapshot.read_text().splitlines()if l.startswith('{')]
checkpoints=[e for e in events if e['event']=='checkpoint'and e['step']==14000]
assert [e['phase']for e in checkpoints]==['snapshot-start']+['cpu-snapshot']*4+['complete']
last_step=max(e['step']for e in events if e['event']=='train');assert last_step>14000
receipt={'recorded_UTC':datetime.now(timezone.utc).isoformat(),'producer':reference(__file__),
 'production_plan':reference(root/'production-handoff-plan-v7.json'),'actual_checkpoint':reference(out/'step014000.pt'),
 'launch':reference(root/'production-handoff-v7/00-scale-control20k-launch.json'),'owner':{'pid':p.pid,'create_time':p.create_time()},
 'raw_tensors':91,'EMA_tensors':91,'Adam_states':89,'all_Adam_steps':14000,'all_values_finite':True,
 'Python_CPU_CUDA_RNG_present':True,'all_serialized_tensors_CPU':True,'original_horizon':20000,'batch_size':16,
 'checkpoint_events':checkpoints,'last_observed_train_step':last_step,'log_snapshot':reference(snapshot),
 'scope':'First actual full production checkpoint after CPU-snapshot repair, separately verified from transport qualification. Training advances beyond14k. No model quality/full-horizon/duration claim; future reliability remains observed, not guaranteed. Source and failed partial bytes unchanged; large checkpoint remains local.'}
write_json(out/'result.json',receipt)
dest=repo/'docs/results/full-corpus-checkpoint-cpu-recovery-v1';sources=[]
for source,name in [(Path(__file__).resolve(),'step14000-verifier.py'),(snapshot,'step14000-log-snapshot.log')]:
    path=dest/name;shutil.copyfile(source,path);assert reference(path)['sha256']==reference(source)['sha256'];sources.append({'original':reference(source),'published':reference(path)})
write_json(dest/'step14000-addendum.json',{'publication':reference(dest/'publication.json'),'receipt':receipt,'exact_source_addendum':sources})
print('Actual14k production checkpoint complete',receipt['actual_checkpoint']['sha256'],'save_seconds',checkpoints[-1]['seconds'],'training',last_step)
