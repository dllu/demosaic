"""Evaluate a declared equal Tiny/Small prediction mean from saved FP32 arrays."""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil

from audit_quality_archive import _triplet, binding, paired_changes, write
from compare_quality_archives import METHOD_FIELDS, canonical, normalize_row
from demosaic import archive_metrics
from demosaic.prediction_archive import PredictionArchive, fingerprint

REPO = Path(__file__).absolute().parents[1]
BASE = REPO / ".cache/current-quality-20261023-v1"
DIGESTS = {"V114": "2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2",
           "V115": "fee5d05c599cb32f5a1e587c31979f040a06152c8e14676481eee83a4ce04d84",
           "V117": "f69452432a852ac4c5ffdcbf7d6fe6837a3ab46adbc8a7fdae073111220b8ab0"}
COUNTS = {"known": (24, 72), "unseen": (30, 90), "photo": (3108, 12404),
          "texture": (112, 448), "color": (1176, 1176)}
MATERIALS = ("0ae232278265dabbdd54f52c34045a3d03323aa7", "212ae12913effa23268af953b4c8f8e8b7ab4ef5")


def read(path):
    return json.loads(Path(path).read_text())


def checked(item):
    if binding(item["path"]) != item:
        raise ValueError(f"Changed mean-comparison evidence: {item['path']}")
    return Path(item["path"])


def prepare(root):
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and "torch" not in sys.modules
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    assert shutil.disk_usage(root.parent).free >= 128 * 2**30
    definition = {"name": "V115+V117 mean", "operator": "(V115_FP32 + V117_FP32) * float32(0.5)",
                  "space": "linear-camera-RGB before clipping/rendering", "weights": [.5, .5],
                  "component_checkpoint_sha256": [DIGESTS["V115"], DIGESTS["V117"]],
                  "component_policy": "none", "fitted_to_targets": False}
    import hashlib
    definition_sha = hashlib.sha256(canonical(definition).encode()).hexdigest()
    old = read(BASE / "V112-continuations-independent-audit-v2/result-v1.json")
    new = read(BASE / "V117-V118-band-independent-audit-v1/result-v1.json")
    stages, inputs = {}, [binding(BASE / "V112-continuations-independent-audit-v2/result-v1.json"),
                          binding(BASE / "V117-V118-band-independent-audit-v1/result-v1.json")]
    for stage in COUNTS:
        stages[stage] = {}
        for label, original in [("V115", old), ("V117", new)]:
            audit_ref = original["stages"][stage]
            audit = read(checked(audit_ref))
            inputs.extend([audit_ref, audit["manifest"], audit["report"], audit["independent_rows"]])
            stages[stage][label] = {"audit": audit_ref, "archive": audit["manifest"],
                                    "report": audit["report"], "rows": audit["independent_rows"]}
        stages[stage]["V114_rows"] = read(checked(old["stages"][stage]))["independent_rows"]
    evaluation = read(BASE / "V117-V118-band-quality-v1/evaluation-plan-v1.json")
    source_manifest = evaluation["stages"]["photo"]["manifest"]
    inputs.append(source_manifest)
    prior = BASE / "fixed-V115-V117-mean-v1/failure-v1.json"
    if prior.exists():
        assert read(prior)["actual_saved_batch_means"] == 0
        inputs.extend([binding(prior),binding(prior.parent/"plan-v1.json"),binding(prior.parent/"run-v1.log")])
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    sources = ["scripts/evaluate_fixed_prediction_mean.py", "scripts/audit_quality_archive.py",
               "scripts/compare_quality_archives.py", "src/demosaic/__init__.py",
               "src/demosaic/archive_metrics.py", "src/demosaic/prediction_archive.py", "src/demosaic/safety.py"]
    for source in sources:
        destination = work / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / source, destination)
        destination.chmod(0o444)
    plan = {"root": str(root), "work": str(work), "artifact_root":str(work/"artifacts"),
            "definition": definition, "operator_definition_sha256": definition_sha,
            "stages": stages, "source_manifest": source_manifest, "counts": COUNTS,
            "driver": binding(work / "scripts/evaluate_fixed_prediction_mean.py"),
            "inputs": list({i["path"]: i for i in inputs}.values()),
            "frozen_files": [binding(p) for p in work.rglob("*.py")],
            "maximum_seconds": 3600, "minimum_available_RAM_GiB": 24, "minimum_internal_free_GiB": 96,
            "new_neural_forwards": 0, "new_noise_observations": 0, "RAW_decodes": 0, "optimizer_updates": 0,
            "prior_failed_attempt":binding(prior) if prior.exists() else None,
            "layout_correction":"Preserve the v1 zero-mean output-root failure. The corrected attempt writes archives under its frozen work/artifacts repository; the fixed numerical operator is unchanged.",
            "scope": "One prospective fixed equal V115 Small / V117 Tiny output mean, with no coefficient search/target fitting. Reuse completed matched single-view FP32 predictions and exact targets only. Full five numerical stages, source/scene-balanced component/general comparisons and two native exact-GT triplets. Not a new trained checkpoint, architecture selection or real-camera superiority claim. Native viewing and interpretation follow; V119 and all original jobs remain unchanged."}
    path = root / "plan-v1.json"
    write(path, plan)
    return path


def guard(plan):
    for item in [*plan["inputs"], *plan["frozen_files"]]:
        checked(item)


def observation_key(row, stage):
    if stage == "color":
        return row["case"],
    return row["id" if stage in {"photo", "texture"} else "tile_id"], row.get("condition"), row["pattern"]


def selected_records(item, digest):
    records = {}
    for index, line in enumerate(checked(item).read_text().splitlines()):
        row = json.loads(line)
        assert row["schema"] == "demosaic-predictions-v1" and row["index"] == index
        if row["model"]["sha256"] == digest and row["model"]["self_ensemble"] == "none":
            key = canonical(row["context"])
            assert key not in records
            records[key] = row
    return records


def arrays(record, archive):
    archive_root = Path(archive["path"]).parent.resolve()
    for key in ("prediction", "supervision"):
        assert Path(record[key]["path"]).resolve().is_relative_to(archive_root)
        checked(record[key])
    prediction = np.load(record["prediction"]["path"], allow_pickle=False)
    with np.load(record["supervision"]["path"], allow_pickle=False) as data:
        supervision = {k: data[k] for k in data.files}
    assert fingerprint(prediction) == record["prediction_values"]
    assert {k:fingerprint(v) for k,v in supervision.items()} == record["supervision_values"]
    return prediction, supervision


def controls(spec, stage):
    result = {}
    for label in ("V114", "V115", "V117"):
        item = spec["V114_rows"] if label=="V114" else spec[label]["rows"]
        rows = [normalize_row(r,stage) for r in read(checked(item)) if r["checkpoint_sha256"] == DIGESTS[label]]
        index = {observation_key(r,stage):r for r in rows}
        assert len(index) == len(rows) and rows
        result[label] = index
    return result


def run(path):
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and "torch" not in sys.modules
    os.nice(10)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    plan = read(path)
    assert binding(__file__) == plan["driver"]
    guard(plan)
    root = Path(plan["root"])
    artifact_root = Path(plan["artifact_root"])
    artifact_root.mkdir(exist_ok=False)
    (root / "run.claim").open("x").close()
    start = time.monotonic()
    assert psutil.virtual_memory().available >= 48 * 2**30
    assert shutil.disk_usage(root).free >= 128 * 2**30
    descriptor = {"label": plan["definition"]["name"], "sha256": plan["operator_definition_sha256"], "self_ensemble": "none",
                  "kind": "fixed-output-mean", "identity_kind": "operator-definition-sha256", "definition": plan["definition"]}
    sources = {r["id"]:r for r in (json.loads(s) for s in checked(plan["source_manifest"]).read_text().splitlines())}
    stages, completed, max_rounding, batches = {}, {}, 0.0, 0
    owner = {"pid":os.getpid(),"created":process.create_time()}

    def resource():
        assert time.monotonic()-start < plan["maximum_seconds"]
        assert psutil.virtual_memory().available >= plan["minimum_available_RAM_GiB"]*2**30
        assert shutil.disk_usage(root).free >= plan["minimum_internal_free_GiB"]*2**30

    try:
        for stage,spec in plan["stages"].items():
            output = artifact_root / stage
            output.mkdir(exist_ok=False)
            archive = PredictionArchive(output / "archive")
            a = selected_records(spec["V115"]["archive"],DIGESTS["V115"])
            b = selected_records(spec["V117"]["archive"],DIGESTS["V117"])
            assert a.keys()==b.keys() and len(a)==COUNTS[stage][0]
            baseline = controls(spec,stage)
            original = read(checked(spec["V117"]["report"]))
            border = original.get("border",32) if stage in {"known","unseen"} else original.get("protocol",{}).get("border",8)
            rows, triplets, proof_error = [], [], 0.0
            for index,key in enumerate(a):
                resource()
                pa,ta = arrays(a[key],spec["V115"]["archive"])
                pb,tb = arrays(b[key],spec["V117"]["archive"])
                assert a[key]["supervision_values"] == b[key]["supervision_values"]
                assert ta.keys()==tb.keys() and all(np.array_equal(ta[k],tb[k]) for k in ta)
                assert pa.shape==pb.shape and pa.dtype==pb.dtype==np.float32
                prediction = (pa+pb)*np.float32(.5)
                assert np.isfinite(prediction).all()
                exact = (pa.astype(np.float64)+pb.astype(np.float64))*.5
                rounding = float(np.max(np.abs(prediction-exact)))
                assert rounding <= float(np.max(np.abs(np.spacing(prediction))))*.5+np.finfo(np.float32).tiny
                max_rounding = max(max_rounding,rounding)
                target = ta["reference_rgb" if stage in {"known","unseen"} else "target"].astype(np.float64)
                decomposition = .5*((pa.astype(np.float64)-target)**2+(pb.astype(np.float64)-target)**2)-.25*(pa.astype(np.float64)-pb.astype(np.float64))**2
                delta = float(abs(np.mean((exact-target)**2)-np.mean(decomposition)))
                proof_error = max(proof_error,delta)
                assert delta < 1e-12
                context = a[key]["context"]
                saved = archive.append(descriptor,context,prediction,ta)
                if stage=="color":
                    measures = archive_metrics.color(prediction,ta)
                elif stage=="texture":
                    measures = archive_metrics.texture(prediction,ta,period=context["period"] if context["kind"]=="carrier" else None)
                else:
                    measures = archive_metrics.photometry(prediction,ta,border=border,camera=stage in {"known","unseen"})
                for j,identity in enumerate(context["ids"]):
                    lookup = (context["case_index"],) if stage=="color" else (identity,context.get("condition",{}).get("name"),context["pattern"])
                    reference = baseline["V117"][lookup]
                    metadata = {k:v for k,v in reference.items() if k not in METHOD_FIELDS}
                    scores = measures if stage=="color" else {k:None if np.isnan(v[j]) else float(v[j]) for k,v in measures.items()}
                    rows.append({**metadata,"model":descriptor["label"],"checkpoint_sha256":descriptor["sha256"],"metrics":scores,
                                 **({"model_index":0} if stage=="color" else {})})
                    if (stage=="photo" and identity in MATERIALS and context["condition"]["name"]=="iso12800-prior" and context["pattern"]=="RGGB"):
                        triplets.append(_triplet(output,saved,prediction,ta,j,sources[identity]))
                batches += 1
                if (index+1)%100==0:
                    print({"stage":stage,"completed_saved_batch_means":index+1,"new_neural_forwards":0},flush=True)
            assert len(rows)==COUNTS[stage][1]
            assert archive.verify_alignment()["records"]==COUNTS[stage][0]
            report = {"models":[descriptor],"checkpoints":[descriptor],"protocol":original.get("protocol",{}),"border":border}
            row_name = {"photo":"per-image.jsonl","known":"per-crop.jsonl","unseen":"per-crop.jsonl","texture":"per-case.jsonl"}.get(stage)
            if row_name:
                with (output/row_name).open("x") as stream:
                    for row in rows:stream.write(json.dumps(row,allow_nan=False)+"\n")
            else:
                report["results"] = rows
            write(output/("report.json" if stage=="color" else "summary.json"),report)
            contrasts = {}
            if stage in {"photo","known","unseen"}:
                metrics = ("srgb_psnr","linear_psnr","chroma_mae","gradient_mae") if stage=="photo" else ("sensor_psnr","ahd_srgb_psnr","ahd_chroma_mae","ahd_gradient_mae")
                for label,control in baseline.items():
                    contrasts[label] = []
                    for metric in metrics:
                        candidate, matched, missing = [], [], 0
                        for row in rows:
                            other = control[observation_key(row,stage)]
                            values = row["metrics"][metric],other["metrics"][metric]
                            assert (values[0] is None)==(values[1] is None)
                            if values[0] is None:
                                missing += 1
                            else:
                                candidate.append(row)
                                matched.append(other)
                        assert candidate
                        contrasts[label].append({**paired_changes(candidate,matched,stage=stage,metric=metric),
                                                 "shared_invalid_observations":missing})
            result = {"stage":stage,"plan":binding(path),"archive":binding(archive.manifest),"observations":len(rows),
                      "batch_means":len(a),"operator":descriptor,"component_comparisons":contrasts,"native_triplets":triplets,
                      "maximum_unclipped_MSE_decomposition_error":proof_error,"new_neural_forwards":0}
            write(output/"result-v1.json",result)
            completed[stage] = binding(output/"result-v1.json")
            stages[stage] = result
            print({"stage_completed":stage,"observations":len(rows),"new_neural_forwards":0},flush=True)
        assert batches==4450 and len(stages["photo"]["native_triplets"])==2
        assert "torch" not in sys.modules
        guard(plan)
        write(root/"result-v1.json",{"status":"completed-fixed-prediction-mean-five-stages-native-review-pending","owner":owner,
              "plan":binding(path),"completed":completed,"definition":plan["definition"],"operator_definition_sha256":plan["operator_definition_sha256"],
              "batch_means":batches,"observations":14190,"maximum_FP32_mean_rounding_error":max_rounding,
              "elapsed_seconds":time.monotonic()-start,"Torch_imported":False,"new_neural_forwards":0,"new_noise_observations":0,
              "RAW_decodes":0,"optimizer_updates":0,"scope":plan["scope"]})
    except BaseException as error:
        write(root/"failure-v1.json",{"owner":owner,"plan":binding(path),"completed_stages":completed,
              "actual_saved_batch_means":batches,"error":repr(error),"new_neural_forwards":0,
              "scope":"Preserve actual partial CPU operator evidence; no neural inference or automatic retry."})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("prepare","run"))
    parser.add_argument("path",type=Path)
    args=parser.parse_args()
    result={"prepare":prepare,"run":run}[args.mode](args.path)
    if result is not None:print(result,flush=True)
