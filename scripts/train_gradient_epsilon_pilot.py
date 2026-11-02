"""Check and train V141 against saved V129 inputs without changing its old run."""

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
import yaml
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import prepare as prepare_recipes
from train_reviewed_shadow_trial import worker
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
CONTROL = REPO / ".cache/current-quality-20261023-v1/reviewed-detail-training-pilot-v1/run"


def prepare(root):
    recipe = REPO / "configs/quality-v120-gradient-epsilon-pilot-v141.yaml"
    config = yaml.safe_load(recipe.read_text())
    baseline = yaml.safe_load(
        (REPO / "configs/quality-v120-reviewed-detail-pilot-v129.yaml").read_text()
    )
    ignored = {"run", "experiment_notes", "gradient_charbonnier_epsilon"}
    assert {k: v for k, v in config.items() if k not in ignored} == {
        k: v for k, v in baseline.items() if k not in ignored
    }
    assert config["gradient_charbonnier_epsilon"] == 0.00003
    assert config["reconstruction_charbonnier_epsilon"] == 0.0003
    path = prepare_recipes(root, root / "work/artifacts", [recipe])
    plan = read(path)
    work = Path(plan["work"])
    for name in ("train_reviewed_shadow_trial.py", Path(__file__).name):
        shutil.copyfile(REPO / "scripts" / name, work / "scripts" / name)
    for phase in ("CPU", "CUDA"):
        p = Path(plan["arms"]["V141"][phase])
        actual = yaml.safe_load(p.read_text())
        if phase == "CPU":
            actual["patch_size"] = 128
        p.write_text(yaml.safe_dump(actual, sort_keys=False))
        for name, value in (("inherited", None), ("invalid", 0)):
            changed = {
                **actual,
                "gradient_charbonnier_epsilon": value,
                "run": actual["run"] + "-rejected-" + name,
            }
            dest = work / "configs" / f"{phase}-V141-rejected-{name}.yaml"
            dest.write_text(yaml.safe_dump(changed, sort_keys=False))
            plan["arms"]["V141"][f"{phase}_rejected_{name}"] = str(dest)
    controls = {}
    for phase in ("CPU", "CUDA", "train"):
        p = CONTROL / f"{phase}-V129-result.json"
        result = read(p)
        assert result["arm"] == "V129" and result["model_EMA_Adam_finite"]
        assert result["updates"] == (1000 if phase == "train" else 18)
        assert (
            not live(result["owner"]) and ref(result["checkpoint"]["path"]) == result["checkpoint"]
        )
        controls[phase] = ref(p)
    plan.update(
        worker_script=ref(work / "scripts" / Path(__file__).name),
        core_worker_script=ref(work / "scripts/train_reviewed_shadow_trial.py"),
        smoke_updates=16,
        resume_new_updates=2,
        arm_fractions={"V141": 0.0},
        restoration_tensors_by_arm={"V141": 91},
        saved_control_arm="V129",
        matched_control_results=controls,
        require_matched_clean_inputs=True,
        require_matched_noisy_inputs=True,
        capture_initial_outputs=True,
        require_equal_initial_outputs=False,
        resume_rejection_changes=["inherited", "invalid"],
        resume_rejection_error_keyword="epsilon",
        rejection_result_key="changed_gradient_resume_rejections",
        phase_result_status="completed-small-gradient-epsilon-pilot-phase",
        CUDA_allocator_cap_GiB=12,
        maximum_smoke_worker_seconds=1800,
        maximum_train_worker_seconds=28800,
        prospective_domain_batches=read(CONTROL / "plan.json")["prospective_domain_batches"],
        scope="Fresh V1411000 from V120, identicalV12990782/27 seed70/quota.5/zeroPSF/native256B16BF16/"
        "LR1e-5/warm100 recipe. Only spatial-gradient Charbonnier epsilon3e-4→3e-5; "
        "all other coefficients/pixel epsilons and paired objective unchanged. "
        "All1000 clean/noisy batches must match actualV129; CPU128B1/CUDA256B16 "
        "discarded16+2 checks first. 12GiB CUDA cap,40/50GiB CPU/CUDA launch,32GB runtime floor, "
        "original8h production bound, no automatic retry/schedule reset. Native/GFX/exact-flat quality pending.",
    )
    plan["inputs"] += [*controls.values(), ref(CONTROL / "plan.json")]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


def run(path):
    plan = read(path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(path),
        "completed": {},
    }

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "status.json", state)

    child = None
    try:
        for phase in ("CPU", "CUDA", "train"):
            guard(plan)
            assert psutil.virtual_memory().available >= (40 if phase == "CPU" else 50) * 2**30
            assert shutil.disk_usage(root).free >= 128 * 2**30
            assert shutil.disk_usage("/mnt/external").free >= 208 * 2**30
            env = dict(
                os.environ,
                CUDA_VISIBLE_DEVICES="" if phase == "CPU" else "0",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OPENBLAS_NUM_THREADS="1",
                OMP_NUM_THREADS="2",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
                PYTHONDONTWRITEBYTECODE="1",
                PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
            )
            with (root / f"{phase}-V141.log").open("x") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        plan["worker_script"]["path"],
                        "worker",
                        str(path),
                        "--phase",
                        phase,
                    ],
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                record(
                    "running-gradient-epsilon-pilot",
                    phase=phase,
                    child={"pid": child.pid, "created": psutil.Process(child.pid).create_time()},
                )
                assert (
                    child.wait(
                        timeout=plan["maximum_train_worker_seconds"]
                        if phase == "train"
                        else plan["maximum_smoke_worker_seconds"]
                    )
                    == 0
                )
            result_path = root / f"{phase}-V141-result.json"
            result = read(result_path)
            assert result["status"] == plan["phase_result_status"]
            assert result["all_observed_inputs_match_saved_control"] and not live(result["owner"])
            assert (
                result["updates"] == result["all_AdamW_steps"] == (1000 if phase == "train" else 18)
            )
            state["completed"][phase] = ref(result_path)
            record("completed-gradient-epsilon-phase", child=None)
            print(phase, "completed", flush=True)
        record("completed-gradient-epsilon-training-awaiting-quality-review", child=None)
    except BaseException as error:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGINT)
            child.wait(timeout=30)
        record("failed-gradient-epsilon-pilot-no-automatic-retry", child=None, error=repr(error))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("prepare", "run", "worker"))
    p.add_argument("path", type=Path)
    p.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    args = p.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "run":
        run(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, "V141")
