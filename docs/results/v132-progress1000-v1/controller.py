import os,sys,time
from pathlib import Path
import psutil
from train_directional_bank_trial import read,ref,guard,save
from train_v43_quality_trial import live
from queue_raw_spatial_endpoints import run_child
path=Path(sys.argv[1]);plan=read(path);guard(plan);root=Path(plan['root']);work=Path(plan['work'])
(root/'controller.claim').open('x').close()
state={'plan':ref(path),'owner':{'pid':os.getpid(),'created':psutil.Process().create_time()}}
def record(status,**details):
 state.update(status=status,updated_unix=time.time(),**details);save(root/'status.json',state)
try:
 s=read(plan['training_status']);assert s['plan']==plan['training_plan'] and s['owner']==plan['training_owner'] and s['child']==plan['training_worker'] and s['arm']=='V132' and live(s['child'])
 record('starting-exact-retained-progress-collection',child=None)
 for name,args,cuda in [('collect_retained_checkpoint_pilot.py',[str(path)],True),('report_checkpoint_pilot.py',[str(path),str(root/'collection-v1.json')],False),('audit_checkpoint_pilot.py',[str(root)],False),('stage_full_model_endpoint.py',[str(root),str(root/'native-stage')],False),('render_endpoint_faint_crops.py',[str(root),str(root/'faint-amplified20'),'--contrast','20'],False)]:
  run_child(plan,record,[plan['python'],'-P',str(work/'scripts'/name),*args],work,root/(name+'.log'),cuda=cuda,timeout=plan['maximum_collector_seconds']if cuda else plan['maximum_CPU_analysis_seconds'])
  if cuda:
   c=read(root/'collection-v1.json');assert c['plan']==ref(path) and c['counts']=={'root':102,'encoder':102} and c['progress_checkpoint_verified'] and c['RNG_unchanged']
  if name=='audit_checkpoint_pilot.py':assert read(root/'independent-audit-v1.json')['status']=='passed-independent-FFT-metric-and-native-pixel-audit'
 record('completed-progress-report-audit-and-staging-awaiting-actual-viewing',child=None,collection=ref(root/'collection-v1.json'),audit=ref(root/'independent-audit-v1.json'))
except BaseException as error:
 record('failed-progress-review-preserved-no-automatic-retry',error=repr(error),child=None);raise
