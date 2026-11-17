"""Evaluate the first equal-budget long-cosine milestone while training continues."""
import os
import subprocess
import sys
import time
from pathlib import Path
import numpy as np
import psutil
from demosaic.experiments.artifacts import checked,read_json,reference,verify_plan,write_json

queue_path = Path(sys.argv[1])
queue = read_json(queue_path)
verify_plan(queue)
assert reference(__file__) == queue["watcher"]
root = Path(queue["root"])
os.sched_setaffinity(0, [6,7])
expected = read_json(checked(queue["training_launch"]))
receipt_path = Path(queue["expected_state_receipt"])
deadline = time.monotonic() + 21600
while not receipt_path.exists():
    owner = psutil.Process(expected["pid"])
    if owner.create_time() != expected["create_time"] or owner.status() == psutil.STATUS_ZOMBIE:
        raise RuntimeError("Owned trainer no longer matches launch. No restart.")
    if time.monotonic() > deadline:
        raise TimeoutError("Milestone observation deadline reached. No trainer changes.")
    time.sleep(10)

state_binding = reference(receipt_path)
state = read_json(checked(state_binding))
assert state["global_step"] == 20000 and state["LR_horizon"] == 100000
checked(state["checkpoint"])
old = read_json(checked(queue["native_template"]))
work = Path(queue["work"])
plan = {
    **old, "root": str(root), "work": str(work),
    "frozen_files": queue["frozen_files"],
    "inputs": [reference(queue_path),state_binding,state["checkpoint"],*old["inputs"]],
    "collector": reference(work/"scripts/collect_full_corpus_checkpoint_review.py"),
    "models": {**old["models"],"scale-long20k":{
        "checkpoint":state["checkpoint"],"step":20000,"weights":"EMA","display_label":"Long schedule20k EMA",
        "retained_progress":True,"training_horizon":100000}},
    "training_plan": queue["training_plan"], "retained_checkpoint_receipt":state_binding,
    "triplet_model":"scale-long20k", "planned_root_calls":330, "planned_DINO_executions":110,
    "scope":"First equal-20k-budget long-cosine milestone vs. current V120 and short-cosine20k."
            " Same110 retained cases,all three fresh matched CPU EMA inputs. Existing native B1"
            " two-thread policy. Explicit milestone, not completed100k or primary427.",
}
path=root/"plan.json"
write_json(path,plan)
env = {**os.environ, "CUDA_VISIBLE_DEVICES":"", "PYTHONPATH":f"{work}/scripts:{work}/src",
       "OPENBLAS_NUM_THREADS":"2","OMP_NUM_THREADS":"2"}
for name,args in [("collection",["collect_full_corpus_checkpoint_review.py",str(path)]),
                  ("report",["report_full_corpus_checkpoint_review.py",str(root)])]:
    with (root/(name+".log")).open("xb")as log:
        child=subprocess.Popen([sys.executable,str(work/"scripts"/args[0]),*args[1:]],
                               env=env,stdout=log,stderr=subprocess.STDOUT)
        write_json(root/(name+"-launch.json"),{"pid":child.pid,
                   "create_time":psutil.Process(child.pid).create_time(),"plan":reference(path)})
        rc=child.wait()
    write_json(root/(name+"-return.json"),{"returncode":rc})
    if rc:
        raise RuntimeError(f"{name} failed with return code {rc}")
current=read_json(root/"collection/result.json")
prior=read_json(checked(queue["closed_controls"]))
assert len(current["records"])==len(prior["records"])==110
for now,then in zip(current["records"],prior["records"],strict=True):
    a,c=(read_json(checked(item))for item in (now,then))
    assert a["id"]==c["id"] and a["input_fingerprints"]==c["input_fingerprints"]
    for old_variant,new_variant in zip(c["variants"],a["variants"][:2],strict=True):
        assert old_variant["checkpoint"]==new_variant["checkpoint"] and old_variant["label"]==new_variant["label"]
        np.testing.assert_array_equal(np.load(checked(old_variant["prediction"])),
                                      np.load(checked(new_variant["prediction"])))
write_json(root/"completed.json",{"plan":reference(path),"result":reference(root/"report/result.json"),
    "prior_controls":queue["closed_controls"],"control_predictions_bitexact":220,
    "scope":"All110 retained cases,330 matched CPU roots and two fresh control arms agree bit-exactly"
            " with original outputs. Numerical report prepared. Independent quality and actual"
            " native review pending. Training process remains independent."})
