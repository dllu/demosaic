"""One V180 local-evidence continuation, reusing completed V178 comparisons.

The exact frozen V178 training engine is configured explicitly with the local
operator. Its old network Adam/EMA history and cached 900-update recipe remain.
No old arm or admission probe is repeated as training.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V180-local-phase-trial-v1"
ADMISSION = REPO / ".cache/quality-20261107/V180-local-phase-admission-v1"
MATCHED = REPO / ".cache/quality-20261107/V178-phase-evidence-trial-v1"
ARMS = ["evidence"]
METHODS = {"evidence": {e: f"V180-local-phase-{e}" for e in ["raw", "EMA"]}}


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def progress(name, value):
    path = ROOT / f"{name}-status-v1.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(value, observed_unix_UTC=time.time()), indent=2) + "\n")
    temporary.replace(path)


def own():
    return {"pid": os.getpid(), "created": psutil.Process().create_time()}


def guard(plan):
    assert ref(__file__) == plan["runner"], "Use the sealed local trial entry"
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest


def prerequisites(plan, name):
    result = read(plan["admission"]["path"])
    assert result["status"].startswith("pass-V180-native-CUDA") and not owner_live(result["owner"])
    assert read(plan["admission_inspection"]["path"])["status"].startswith(
        "pass-actual-terminal-V180"
    )
    assert name in ["evidence-train", "review"]
    if name == "review":
        assert not (ROOT / "evidence-train-failure-v1.json").exists()
        training = read(ROOT / "evidence-train-result-v1.json")
        launch = read(ROOT / "evidence-train-launch-v1.json")
        assert training["owner"] == launch["owner"] and not owner_live(launch["owner"])
        assert training["status"] == "completed-matched-warmstart-one-pass"


def factory(arm, config):
    from demosaic.late_local_phase_evidence_matching import LateLocalPhaseEvidenceMatchingDetail

    if arm != "evidence":
        raise ValueError(arm)
    return LateLocalPhaseEvidenceMatchingDetail(**config)


def configure_engine(plan):
    binding = plan["training_engine"]
    assert ref(binding["path"]) == binding
    assert Path(binding["path"]).is_relative_to(Path(plan["work"]))
    spec = importlib.util.spec_from_file_location(
        "v180_frozen_matching_training_engine", binding["path"]
    )
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    # Explicit module-local dependency injection; original engine bytes stay exact.
    engine.ROOT, engine.ADMISSION = ROOT, ADMISSION
    engine.ARMS, engine.METHODS = ARMS, METHODS
    engine.factory, engine.guard, engine.prerequisites = factory, guard, prerequisites
    return engine


def prepare():
    from admit_local_phase_evidence_matching import dependency_readiness

    dependency = dependency_readiness(MATCHED)
    admission = read(ADMISSION / "admission-result-v1.json")
    assert not owner_live(admission["owner"]) and admission["status"].startswith(
        "pass-V180-native-CUDA"
    )
    inspection = read(ADMISSION / "CPU-inspection-v1.json")
    assert inspection["admission"] == ref(ADMISSION / "admission-result-v1.json") and inspection[
        "status"
    ].startswith("pass-actual-terminal-V180")
    assert not ROOT.exists()
    assert shutil.disk_usage(REPO).free > (48 + 0.5 + 1.2) * 2**30
    assert shutil.disk_usage("/mnt/external").free > (111 + 0.5) * 2**30
    assert psutil.virtual_memory().available > 52 * 2**30
    baseline = read(MATCHED / "plan-v1.json")
    admitted = read(ADMISSION / "plan-v1.json")
    for path, digest in admitted["frozen_files"].items():
        if "/src/demosaic/" in path:
            assert ref(REPO / "src/demosaic" / Path(path).name)["sha256"] == digest

    import torch
    from phase_evidence_training_state import warm_start_matching
    from profile_raw_kernel_inference import model_hash
    from train_local_noise_matching_trial import tree_equal

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    checkpoint = torch.load(
        baseline["initial_checkpoint"]["path"], map_location="cpu", weights_only=True
    )
    model = factory("evidence", admitted["module_config"])
    optimizer, ema, proof = warm_start_matching(
        model, checkpoint, lr=baseline["lr"], weight_decay=baseline["weight_decay"]
    )
    assert proof["initial_updates"] == 900 and proof["Adam_clocks"]["network"]["steps"] == [900.0]
    assert (
        proof["Adam_clocks"]["adapter"]["states"] == 0
        and proof["Adam_clocks"]["adapter"]["tensors"] == 1
    )
    assert tree_equal(optimizer.state_dict()["state"], checkpoint["optimizer"]["state"])
    assert all(
        torch.equal(value, model.state_dict()[name]) for name, value in checkpoint["models"].items()
    )
    assert all(
        torch.equal(value, ema["network." + name]) for name, value in checkpoint["ema"].items()
    )
    proof.update(
        module_hash=model_hash(model),
        component=type(model).__name__,
        trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
        trainable_tensors=sum(p.requires_grad for p in model.parameters()),
        EMA_tensors=len(ema),
    )
    assert proof["module_hash"] == baseline["CPU_warmstart_proof"]["evidence"]["module_hash"]
    assert not torch.cuda.is_initialized()
    ROOT.mkdir()
    work = ROOT / "work"
    for name in ["src", "scripts"]:
        shutil.copytree(
            REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    for directory in ["checkpoints", "native"]:
        (ROOT / "artifacts" / directory).mkdir(parents=True)
    engine = ref(work / "scripts/train_phase_evidence_trial.py")
    assert engine["sha256"] == baseline["runner"]["sha256"]
    plan = {
        k: v
        for k, v in baseline.items()
        if k
        not in [
            "frozen_files",
            "renderer",
            "both_arms_original_moments_and_EMA_exact",
            "admission_plan_at_draft",
        ]
    }
    plan.update(
        status="prepared-single-local-phase-continuation-after-actual-admission",
        created_unix_UTC=time.time(),
        root=str(ROOT),
        work=str(work),
        artifacts=str(ROOT / "artifacts"),
        runner=ref(work / "scripts" / Path(__file__).name),
        training_engine=engine,
        component=proof["component"],
        operator_source=ref(work / "src/demosaic/late_local_phase_evidence_matching.py"),
        module_config=admitted["module_config"],
        methods=METHODS,
        arms=ARMS,
        CPU_warmstart_proof={"evidence": proof},
        admission=ref(ADMISSION / "admission-result-v1.json"),
        admission_inspection=ref(ADMISSION / "CPU-inspection-v1.json"),
        admission_expected_root=str(ADMISSION),
        completed_matched_dependency=dependency,
        matched_plan=ref(MATCHED / "plan-v1.json"),
        matched_scores=ref(MATCHED / "scores-v1.json"),
        prior_figures=ref(MATCHED / "figures-v1.json"),
        projected_new_local_GiB=1.2,
        expected_quality_counts={
            "wrapper": 1644,
            "frozen": 1644,
            "network": 1500,
            "sampler": 7500,
            "projection": 1500,
        },
        scope="One V180 local-evidence variant;completed V178 control/global-evidence raw+EMA are reused comparisons,not rerun or bit-exact paired retraining. Same V172 real900-update raw/Adam/EMA initializer,1000cachedrows/900newupdates/3600images/100ADCskips,same seven-term objective/domain weights/LR/EMA/sampler. Same3120weight adapter as global V178;only coefficient fields become local,window65/stride32 fixed after training-only diagnostic. Existing141network clocks end1800,newadapter900. Training engine source unchanged and configured explicitly via module-local ROOT/ARMS/METHODS/factory/guard/prerequisites bindings. Genuine row8 restore,all5checkpoints,strict endpoint EMA. Both endpoints/all822inputs,144ADCidentities,36full-array native cases. Admission fresh-Adam probes are not training initializers. Protected GFX scenes/JPEGs/siblings excluded training;ISO100refs qualitative/notGT. No fresh noise/source/parent/DINO/RAWdecode or original/dataz access. Sampler atomic backward warn-only nondeterminism;no blind/seed uncertainty claim. Numerical/native quality and independent audits required after workers terminal.",
    )
    plan["inputs"] = (
        baseline["inputs"]
        + [
            plan[k]
            for k in [
                "admission",
                "admission_inspection",
                "matched_plan",
                "matched_scores",
                "prior_figures",
            ]
        ]
        + [dependency["publication"], dependency["verification"]]
    )
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(ROOT / "plan-v1.json", plan)
    print("PreparedV180900updates/3600images/2endpoints;actual141Adam900+adapter0;noCUDA/forward")


def review(engine):
    import numpy as np
    import torch
    from balanced_spatial_metrics import DetailMetrics, summarize
    from phase_evidence_training_state import load_matching_ema
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    owner = own()
    engine.require_worker_launch(plan, "review", owner)
    (ROOT / "review.claim").open("x").close()
    engine.runtime(plan)
    expected = {
        r["id"]: r
        for r in read(plan["prior_scores"]["path"])["rows"]
        if r["method"] == "balanced-EMA"
    }
    assert len(expected) == 822
    metric = DetailMetrics(plan["metrics_sources"])
    design = read(plan["design"]["path"])["observations"]
    counts = {k: 0 for k in ["wrapper", "frozen", "network", "sampler", "projection"]}
    rows = []
    native = {}
    weights = {}
    checkpoints = {}
    replays = ADC_exact = closure_channels = 0
    CPU_RNG, CUDA_RNG = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    with (
        (ROOT / "quality-events-v1.jsonl").open("x") as events,
        (ROOT / "quality-observations-v1.jsonl").open("x") as journal,
    ):
        for arm in ARMS:
            training = read(ROOT / f"{arm}-train-result-v1.json")
            assert training["frozen_unchanged"] and training["RNG_unchanged"]
            checkpoints[arm] = training["final_checkpoint"]
            assert ref(checkpoints[arm]["path"]) == checkpoints[arm]
            state = torch.load(checkpoints[arm]["path"], map_location="cpu", weights_only=True)
            for endpoint in ["raw", "EMA"]:
                method = METHODS[arm][endpoint]
                module = engine.instrument(
                    factory(arm, plan["module_config"]).cuda(), counts
                ).eval()
                module.load_state_dict(state["models"], strict=True)
                if endpoint == "EMA":
                    load_matching_ema(module, state["ema"])
                before = model_hash(module)
                weights[method] = {"before": before, "frozen": model_hash(module.frozen)}
                assert weights[method]["frozen"] == plan["frozen_component"]["module_hash"]
                for ordinal, index in enumerate(plan["processing_order"]):
                    engine.resources(plan, "review", owner)
                    case = design[index]
                    assert (
                        ref(case["arrays"]["path"]) == case["arrays"]
                        and ref(case["parent"]["path"]) == case["parent"]
                    )
                    arrays = dict(np.load(case["arrays"]["path"], allow_pickle=False))
                    base = np.load(case["parent"]["path"], allow_pickle=False)
                    batch = {
                        k: torch.from_numpy(arrays[k]).cuda()
                        for k in ["packed", "variance", "colors", "wb"]
                    }
                    with torch.inference_mode():
                        output, aux = module(
                            torch.from_numpy(base).cuda(),
                            *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                            return_aux=True,
                        )
                    torch.cuda.synchronize()
                    value = output.cpu().numpy()
                    frozen = aux["frozen_output"].cpu().numpy()
                    correction = aux["correction"].cpu().numpy()
                    assert fingerprint(frozen) == expected[case["id"]]["values"]
                    replays += 1
                    np.testing.assert_array_equal(value, frozen + correction)
                    closure_channels += value.size
                    if not aux["matching_evaluated"]:
                        assert np.array_equal(value, frozen) and not np.any(arrays["variance"])
                        ADC_exact += 1
                    row = metric.measure(case, arrays, base, value)
                    row.update(
                        method=method,
                        index=index,
                        values=fingerprint(value),
                        frozen_values=fingerprint(frozen),
                        frozen_replay_exact=True,
                        ADC_exact=not aux["matching_evaluated"],
                        nonlocal_correction_values=fingerprint(correction),
                        nonlocal_correction_RMS_DN16=float(
                            np.sqrt(np.mean(correction.astype(np.float64) ** 2))
                        )
                        * 65535,
                    )
                    if case["id"] in plan["native_cases"]:
                        for label, array in [(method, value), (method + "-correction", correction)]:
                            path = Path(plan["artifacts"]) / "native" / f"{label}-{index:03d}.npy"
                            assert not path.exists()
                            np.save(path, array, allow_pickle=False)
                            native.setdefault(case["id"], {})[label] = ref(path)
                        row["prediction"] = native[case["id"]][method]
                    rows.append(row)
                    evidence = None
                    if arm == "evidence" and aux["phase_evidence"] is not None:
                        evidence = {
                            k: v.detach().cpu().tolist() for k, v in aux["phase_evidence"].items()
                        }
                    record = {
                        "method": method,
                        "index": index,
                        "id": case["id"],
                        "arrays": case["arrays"],
                        "parent": case["parent"],
                        "inputs": {k: fingerprint(arrays[k]) for k in batch},
                        "row": row,
                        "evidence": evidence,
                        "frozen_replay_exact": True,
                        "closure_exact": True,
                    }
                    journal.write(json.dumps(record, allow_nan=False) + "\n")
                    journal.flush()
                    events.write(
                        json.dumps(
                            {
                                "method": method,
                                "index": index,
                                "ordinal": ordinal,
                                "id": case["id"],
                                "counts": dict(counts),
                                "matching_evaluated": aux["matching_evaluated"],
                            }
                        )
                        + "\n"
                    )
                    events.flush()
                    if ordinal % 16 == 0:
                        progress(
                            "review",
                            {
                                "status": "reviewing",
                                "owner": owner,
                                "method": method,
                                "index": index,
                                "counts": counts,
                                "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                            },
                        )
                    del arrays, base, batch, output, aux, value, frozen, correction, evidence
                assert model_hash(module) == before
                weights[method]["after"] = model_hash(module)
                del module
            del state
    assert (
        counts == plan["expected_quality_counts"]
        and len(rows) == 1644
        and len(native) == 36
        and replays == 1644
        and ADC_exact == 144
    )
    assert torch.equal(CPU_RNG, torch.get_rng_state()) and torch.equal(
        CUDA_RNG, torch.cuda.get_rng_state()
    )
    rows.sort(key=lambda r: (r["index"], r["method"]))
    guard(plan)
    save(
        ROOT / "scores-v1.json",
        {
            "status": "completed-two-endpoint-local-phase-fixed-quality-awaiting-native-viewing",
            "owner": owner,
            "plan": ref(ROOT / "plan-v1.json"),
            "checkpoints": checkpoints,
            "rows": rows,
            "summary": summarize(rows),
            "counts": counts,
            "native_predictions": native,
            "module_hashes": weights,
            "weights_unchanged": True,
            "RNG_unchanged": True,
            "exact_V169_replays": replays,
            "ADC_outputs_exact_V169": ADC_exact,
            "independent_inprocess_addition_channels": closure_channels,
            "new_parent_DINO_forwards": 0,
            "new_source_noise_draws": 0,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "scope": plan["scope"],
        },
    )
    progress(
        "review",
        {
            "status": "completed-quality-awaiting-render-and-viewing",
            "owner": owner,
            "counts": counts,
        },
    )


def launch(phase):
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert phase in ["train-evidence", "review"]
    name = phase.removeprefix("train-") + "-train" if phase.startswith("train-") else phase
    prerequisites(plan, name)
    assert not (ROOT / f"{name}-launch-v1.json").exists() and not (ROOT / f"{name}.claim").exists()
    if phase == "review":
        for arm in ARMS:
            result = read(ROOT / f"{arm}-train-result-v1.json")
            assert result["status"].startswith("completed") and not owner_live(result["owner"])
    assert psutil.virtual_memory().available > plan["launch_RAM_GiB"] * 2**30
    env = dict(
        os.environ,
        PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    command = [str(REPO / ".venv/bin/python"), plan["runner"]["path"], phase]
    with (ROOT / f"{name}-v1.log").open("xb") as log:
        child = subprocess.Popen(
            command,
            cwd=REPO,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        save(
            ROOT / f"{name}-launch-v1.json",
            {
                "owner": {"pid": child.pid, "created": psutil.Process(child.pid).create_time()},
                "command": command,
                "plan": ref(ROOT / "plan-v1.json"),
            },
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "phase", choices=["prepare", "train-evidence", "review", "launch-evidence", "launch-review"]
    )
    phase = parser.parse_args().phase
    if phase == "prepare":
        prepare()
        return
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    engine = configure_engine(plan)
    try:
        if phase.startswith("launch-"):
            launch("train-evidence" if phase == "launch-evidence" else "review")
        elif phase == "review":
            review(engine)
        else:
            engine.train("evidence")
    except BaseException as error:
        if phase in ["train-evidence", "review"]:
            name = "evidence-train" if phase == "train-evidence" else "review"
            path = ROOT / f"{name}-failure-v1.json"
            if not path.exists():
                save(
                    path,
                    {
                        "status": "failed-preserved-no-automatic-retry",
                        "owner": own(),
                        "error": repr(error),
                        "source": ref(__file__),
                    },
                )
        raise


if __name__ == "__main__":
    main()
