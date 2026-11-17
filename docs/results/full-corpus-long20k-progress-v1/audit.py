"""Compare source observations, conditioning, and saved states at update 20,000."""
import copy
import json
from collections import Counter
from pathlib import Path
import numpy as np
import psutil
import torch
from demosaic.experiments.artifacts import checked,read_json,reference,write_json

base=Path(".cache/experiments/full-corpus-scaling-v3").resolve()
owner_path=base/"production-handoff-v7/01-scale-long100k-launch.json"
owner=read_json(owner_path);assert psutil.Process(owner["pid"]).create_time()==owner["create_time"]
p=base/"production-handoff-plan-v7.json";training=read_json(p)
initial=Path(training["adopted_states"]["long100k"]["path"]).parent
resume=base/"checkpoint-recovery-v7/work/artifacts/train/long100k/phase-001001-100000"
milestone = resume.parent/"step020000-receipt.json"
saved = read_json(milestone)
assert saved["global_step"] == 20000 and saved["LR_horizon"] == 100000
out=base/"long100k-20k-independent-v1";out.mkdir()
records=[];sources=[]
for phase,start,stop in [(initial,1,1000),(resume,1001,20000)]:
 path=out/f"prefix-{start:06d}-{stop:06d}.jsonl"
 with (phase/"source-crop-observations.jsonl").open() as source,path.open("x")as dest:
  for i in range(start,stop+1):
   line=next(source);row=json.loads(line);assert row["step"]==i
   records.append(row);dest.write(line)
 sources.append(reference(path))
assert len(records)==20000 and [v["global_draw_start"] for v in records]==list(range(0,320000,16))
orders=base.parent/"full-corpus-scaling-v1"
headers=[orders/name/"photo-epoch-order.json"for name in ["order100k","order20k"]]
long,short=map(read_json,headers)
manifest=checked(long["source_manifest"]);assert long["source_manifest"]==short["source_manifest"]
with manifest.open()as stream:
 ids=[v["id"]for line in stream if(v:=json.loads(line))["split"]=="train"]
assert len(ids)==len(set(ids))==90778
order=np.load(checked({"path":headers[0].parent/long["order"]["path"],"sha256":long["order"]["sha256"]}))
ord_counts=Counter();reviewed=Counter();domains=Counter();complete=None
for row in records:
 domains[row["domain"]]+=1
 start=row["global_draw_start"];indices=order[start:start+16]
 if row["domain"]!="commons":
  assert not row["sources"] and np.all(indices==-1);continue
 for sample,i in zip(row["sources"],indices,strict=True):
  if sample["kind"]=="photographic" and sample["reviewed_roi_xywh"] is None:
   assert i>=0 and ids[i]==sample["source_id"]
   ord_counts[sample["source_id"]]+=1
   if complete is None and len(ord_counts)==90778:complete=row["step"]
  else:
   assert i==-1
   if sample["kind"]=="photographic":reviewed[sample["source_id"]]+=1
assert complete==17039 and set(ord_counts)==set(ids)
control=read_json("docs/results/full-corpus-control20k-review-v1/completed-training-audit.json")
old=[]
for bind,start,stop in zip(control["sources"],[1,6001,13001],[6000,13000,20000],strict=True):
 with checked(bind).open()as stream:
  old.extend(row for l in stream if start <= (row:=json.loads(l))["step"] <= stop)
assert len(old)==len(records)
headers_hash=[reference(v)["sha256"]for v in headers]
for current,other in zip(records,old,strict=True):
 x,y=copy.deepcopy(current),copy.deepcopy(other)
 for row,key in [(x,headers_hash[0]),(y,headers_hash[1])]:
  for item in row["sources"]:
   if "photo_epoch_order_sha256" in item:assert item.pop("photo_epoch_order_sha256")==key
 assert x==y
control_conditions={Path(v["path"]).name:v for v in control["conditioning_chunks"]}
conditions=[]
for phase,start,stop in [(initial,1,1000),(resume,1001,20000)]:
 for i in range(start,stop+1,250):
  name=f"conditions-{i:06d}-{i+249:06d}.npz";f=phase/name
  other=control_conditions[name]
  with np.load(f)as a,np.load(checked(other))as b:
   assert a.files==b.files and a["steps"].tolist()==list(range(i,i+250))
   assert a["values"].shape==(250,16,14) and np.isfinite(a["values"]).all()
   for key in a.files:np.testing.assert_array_equal(a[key],b[key])
  conditions.append({"long":reference(f),"control":other})
assert len(conditions)==80
assert sum(ord_counts.values()) == 106823 and sum(reviewed.values()) == 5601
assert Counter(ord_counts.values()) == {1: 74733, 2: 16045}
raw = torch.load(checked(saved["checkpoint"]), map_location="cpu", weights_only=True)
other = torch.load(checked(control["checkpoint"]), map_location="cpu", weights_only=True)
assert raw["step"] == other["step"] == 20000
assert (raw["config"]["steps"], other["config"]["steps"]) == (100000, 20000)
assert len(raw["optimizer"]["state"]) == 89
for state in raw["optimizer"]["state"].values():
    assert state["step"] == 20000
    assert all(torch.isfinite(v).all() for v in state.values() if isinstance(v, torch.Tensor))
assert raw["python_rng"] and raw["torch_rng"].numel() and raw["cuda_rng"]
assert raw["python_rng"] == other["python_rng"]
assert torch.equal(raw["torch_rng"], other["torch_rng"])
assert all(torch.equal(a,b) for a,b in zip(raw["cuda_rng"],other["cuda_rng"],strict=True))
changed = {}
for name in ["model", "ema"]:
    assert raw[name].keys() == other[name].keys() and len(raw[name]) == 91
    assert all(torch.isfinite(v).all() for v in raw[name].values())
    changed[name] = sum(not torch.equal(v,other[name][k]) for k,v in raw[name].items())
    assert changed[name] > 0
write_json(out/"result.json", {"producer":reference(__file__), "training_plan":reference(p),
 "owner":reference(owner_path), "checkpoint":saved["checkpoint"], "retained_receipt":reference(milestone),
 "control_checkpoint":control["checkpoint"], "different_tensors_vs_control":changed,
 "horizons":{"long":100000,"short":20000}, "same_checkpoint_Python_CPU_CUDA_RNG":True,
 "model_EMA_Adam_finite_and_complete": True,
 "snapshots":sources, "source_manifest":long["source_manifest"],
 "order_headers":[reference(q)for q in headers], "first_complete_ordinary_epoch_update":complete,
 "prefix_updates":20000, "target_slots":320000, "ordinary_distinct":len(ord_counts),
 "ordinary_draws":sum(ord_counts.values()), "reviewed_draws":sum(reviewed.values()),
 "reviewed_distinct":len(reviewed), "domain_updates":dict(domains),
 "all_source_crop_seed_rows_match_short_except_header":True, "all80_conditioning_chunks_match":conditions,
 "scope":"Actual equal-budget prefix and saved state on the separate100k trajectory."
         " Native/paired source IDs are unlogged. This does not establish identical full training tensors"
         " or quality. The native evaluation is separate and training continues."})
print(complete,len(ord_counts),sum(ord_counts.values()),sum(reviewed.values()),dict(domains),changed)
