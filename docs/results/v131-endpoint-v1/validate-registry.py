import os,pathlib,json
import numpy as np
import psutil,torch
from demosaic.models.registry import load_model
from demosaic.experiments.artifacts import read_json,write_json,reference,checked,verify_plan
from profile_raw_kernel_inference import model_hash
r=pathlib.Path(__file__).resolve().parent;p=read_json(r/'plan.json');verify_plan({'inputs':[p['checkpoint'],p['observation']['arrays'],p['expected_prediction'],p['frozen_loaded_model']],'frozen_files':p['frozen_files']})
assert psutil.virtual_memory().available>=40*2**30
os.nice(10);os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[-2:]);torch.set_num_threads(2);torch.cuda.set_per_process_memory_fraction(12*2**30/torch.cuda.get_device_properties(0).total_memory)
torch.set_float32_matmul_precision('highest');torch.backends.cuda.matmul.allow_tf32=torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=True;torch.backends.cudnn.deterministic=False;torch.use_deterministic_algorithms(False)
with torch.random.fork_rng(devices=[0]):
 model,state=load_model('v131',checkpoint=p['checkpoint']['path'],expected_sha256=p['checkpoint']['sha256'],device='cuda');model.eval().requires_grad_(False).to(memory_format=torch.channels_last)
 assert state['loaded_sha256']==p['checkpoint']['sha256'] and state['step']==20000
 actual=model.restoration_state_dict();assert len(actual)==91 and actual.keys()==state['ema'].keys();assert all(torch.equal(v.cpu(),state['ema'][k]) for k,v in actual.items());del actual,state
 old=read_json(checked(p['frozen_loaded_model']));full_hash=model_hash(model);backbone_hash=model_hash(model.context.backbone);assert full_hash==old['full_model_sha256'] and backbone_hash==old['backbone_sha256']
 with np.load(checked(p['observation']['arrays']),allow_pickle=False) as a:args=[torch.from_numpy(a[k]).cuda() for k in ['packed','variance','colors','wb','matrix']]
 model.set_noise(p['observation']['noise']['shot'],p['observation']['noise']['read'])
 with torch.inference_mode():pred=model(*args).cpu().numpy()
 expected=np.load(checked(p['expected_prediction']),allow_pickle=False);assert pred.dtype==np.float32 and pred.shape==expected.shape;maximum=float(np.max(np.abs(pred.astype(np.float64)-expected.astype(np.float64))));np.testing.assert_allclose(pred,expected,rtol=0,atol=p['maximum_allowed_absolute_error_camera_RGB']);np.save(r/'registry-prediction.npy',pred);assert model_hash(model)==full_hash
write_json(r/'result.json',{'status':'passed-current-registry-exact-state-and-retained-output-check','plan':reference(r/'plan.json'),'script':reference(__file__),'exact_EMA_tensors':91,'full_model_sha256':full_hash,'backbone_sha256':backbone_hash,'new_registry_root_and_DINO_calls':1,'maximum_absolute_error_camera_RGB':maximum,'maximum_absolute_error_DN16':maximum*65535,'prediction_bits_exact':bool(np.array_equal(pred.view(np.uint32),expected.view(np.uint32))),'prediction':reference(r/'registry-prediction.npy'),'CUDA_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'optimizer_updates':0,'source_noise_draws':0,'scope':p['scope']});print('registry validation passed; maxDN16',maximum*65535,flush=True)
