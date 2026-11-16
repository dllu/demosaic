import json,time,sys,os,hashlib
from pathlib import Path
import psutil
r=Path(sys.argv[1]);launch=json.loads((r/'launch.json').read_text());owner=launch['owner'];deadline=time.time()+16200
def ref(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def save(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2);f.write('\n')
me={'pid':os.getpid(),'created':psutil.Process().create_time()};save(r/'lineage-watcher-owner.json',me)
try:
 while not(r/'finite-scores.json').exists():
  s=json.loads((r/'status.json').read_text());assert s['owner']==owner and s['plan']==launch['plan'];assert not s['status'].startswith('failed')
  process=psutil.Process(owner['pid']);assert process.create_time()==owner['created'] and process.is_running();assert time.time()<deadline;time.sleep(15)
 original=json.loads((r/'finite-scores.json').read_text());derived={**original,'rows':[{**x,'method':'V143'if x['method']=='V120'else x['method']}for x in original['rows']],'original_scores':ref(r/'finite-scores.json'),'lineage_addendum':ref(r/'parent-lineage-addendum.json'),'original_scoring_scope':original['scope'],'scope':'Full384 finite-wire groups across3 priors,8 geometries,2 placements,4 CFAs,2 repeats. Actual parent V143; global/local threshold2. Only parent label/scope corrected, all numeric fields unchanged.'}
 assert all({k:v for k,v in a.items()if k!='method'}=={k:v for k,v in b.items()if k!='method'}for a,b in zip(original['rows'],derived['rows'],strict=True));save(r/'finite-scores-v2.json',derived)
 collection=json.loads((r/'collection.json').read_text());save(r/'collection-v2.json',{**collection,'model':ref(r/'analytic-model-v2.json'),'actual_original_collection':ref(r/'collection.json'),'metadata_correction_only':True,'new_analytic_predictions_in_derivation':0})
 save(r/'lineage-correction-result.json',{'status':'completed-label-only-V143-parent-lineage-correction','original_scores':ref(r/'finite-scores.json'),'corrected_scores':ref(r/'finite-scores-v2.json'),'corrected_collection':ref(r/'collection-v2.json'),'all_numeric_rows_unchanged':True,'new_neural_or_analytic_predictions':0})
except BaseException as error:save(r/'lineage-watcher-failure.json',{'error':repr(error),'no_training_signals':True});raise
