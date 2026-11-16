import os,sys,time,subprocess,signal,json,hashlib
from pathlib import Path
import psutil
r=Path(sys.argv[1]);p=json.loads((r/'plan.json').read_text())
def ref(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def save(status,**kw):
 state.update(status=status,UTC_unix=time.time(),**kw);temp=r/'status.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(r/'status.json')
state={'owner':{'pid':os.getpid(),'created':psutil.Process().create_time()},'plan':ref(r/'plan.json')}
(r/'controller.claim').open('x').close();child=None;identity=None
try:
 for phase,limit in [('predict',p['maximum_prediction_seconds']+120),('score',1800)]:
  env={**os.environ,'PYTHONPATH':p['work']+'/src:'+p['work']+'/scripts','CUDA_VISIBLE_DEVICES':'','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'2'}
  with(r/(phase+'.log')).open('x')as log:
   child=subprocess.Popen([p['python'],'-P',p['script']['path'],phase,str(r)],cwd=p['work'],env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   identity={'pid':child.pid,'created':psutil.Process(child.pid).create_time()};save('running-full-three-prior-local-wave-'+phase,child=identity,deadline_UTC_unix=time.time()+limit);child.wait(timeout=limit)
   if child.returncode:raise RuntimeError('Owned '+phase+' worker exited '+str(child.returncode))
  save('completed-'+phase,child=None)
 save('completed-three-prior-numerical-review-awaiting-native-and-statistical-report',collection=ref(r/'collection.json'),scores=ref(r/'finite-scores.json'),child=None)
except BaseException as error:
 if child is not None and child.poll()is None:
  try:
   current=psutil.Process(identity['pid'])
   if current.create_time()==identity['created']:os.killpg(child.pid,signal.SIGINT);child.wait(timeout=30)
  except psutil.Error:pass
 save('failed-owned-panel-preserved-no-automatic-retry',error=repr(error),child=None);raise
