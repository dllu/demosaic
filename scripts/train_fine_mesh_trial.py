"""Matched V167 bounded heads;only the fine-mesh training distribution differs."""

import argparse
import importlib.util
import json
import math
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from review_v146_window_transfer import relocated_controller_source
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
LIVE_PROGRESS = {}


def prepare(root):
    import numpy as np
    import yaml
    root=root.resolve();assert root.is_relative_to(REPO/'.cache') and root.is_dir()
    assert not (root/'plan-v1.json').exists() and not (root/'work').exists()
    data_plan=read(root/'data-plan-v1.json');guard(data_plan)
    data_path=root/'data-canonical-cache-v1.json';candidate=read(data_path)
    validation=read(root/'data-parent-flag-validation-v1.json')
    assert validation['rows_checked']==171 and validation['counts']=={'parent_root':171,'DINO':171}
    assert candidate['parent_policy_validation']==ref(root/'data-parent-flag-validation-v1.json')
    assert not live(read(root/'data-cache-launch-v1.json')['owner'])
    assert not live(read(root/'data-parent-flag-validation-launch-v1.json')['owner'])
    recipe=REPO/'configs/quality-v143-fine-mesh-ladder-v168.yaml';config=yaml.safe_load(recipe.read_text())
    previous=Path(config['previous_trial']);prior=read(previous/'plan-v1.json');guard(prior)
    shared=config['shared_training_recipe'];assert ref(shared['path'])==shared
    before=yaml.safe_load(Path(shared['path']).read_text())
    assert list(config['arms'])==['legacy-control','fine-mesh']
    assert all(arm==before['arms']['bounded-support'] for arm in config['arms'].values())
    for key in before.keys()-{'version','arms','scope','previous_trial','external_root','internal_reserve_GiB','external_reserve_GiB','shared_training_recipe'}:
        assert config[key]==before[key],key
    cache_path=Path(prior['cache']['path']);cache=read(cache_path)
    assert ref(cache_path)==data_plan['cache'] and len(candidate['batches'])==len(cache['batches'])==1000
    selected={r['step'] for r in data_plan['selected']};unchanged=0
    table=[]
    for old,new in zip(cache['batches'],candidate['batches'],strict=True):
        assert old['step']==new['step'] and old['metadata']['noise']==new['metadata']['noise']
        assert old['metadata']['domain']==new['metadata']['domain']
        if old['step'] in selected:
            assert new['legacy_arrays']==old['arrays'] and new['arrays']!=old['arrays']
        else:assert old==new;unchanged+=1
        variance=np.asarray(new['metadata']['sensor'].get('increment_mean_variance',[]),dtype=np.float32)
        units=np.maximum(np.sqrt(variance),np.float32(2/65535)).reshape(-1,1,1,1)
        table.append({'step':new['step'],'batch':new['arrays'],'shape':list(units.shape),'candidate_units_FP32':units.ravel().tolist()})
    assert unchanged==829
    unit_path=root/'candidate-pair-unit-table-v1.json';save(unit_path,{'rows':table,'cache':ref(data_path),'floor_DN16':2,'scope':'Candidate units reconstructed from actual changed/retained mean increment variances;not restored RGB covariance.'})
    cases=read(previous/'quality-design-v1.json')['observations'];assert len(cases)==822
    per_endpoint=sum(np.load(c['parent']['path'],mmap_mode='r').nbytes+128 for c in cases)
    assert shutil.disk_usage(REPO).free>56.75*2**30
    assert shutil.disk_usage('/mnt/external').free>116.5*2**30+2*per_endpoint
    assert psutil.virtual_memory().available>52*2**30
    work=root/'work';external=Path(config['external_root']);assert external==Path(data_plan['external_root'])
    names=['train_directional_bank_trial.py','train_v43_quality_trial.py','profile_raw_kernel_inference.py','review_v146_window_transfer.py','noisy_objective.py','delivered_spectral_objective.py','robust_spectral_objective.py','local_excess_risk.py','regional_dc_objective.py','paired_response_objective.py','flat_target_anchor.py','pair_unit_floor.py','paired_common_objective.py','paired_common_routing.py','review_fine_mesh_trial.py']
    sources=list((REPO/'src/demosaic').glob('*.py'))+[REPO/'scripts'/n for n in names]
    for source in sources:
        target=work/source.relative_to(REPO);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    runner=work/'scripts'/Path(__file__).name;runner.write_text(relocated_controller_source(Path(__file__).read_text(),REPO))
    target=work/'configs'/recipe.name;target.parent.mkdir(parents=True);shutil.copyfile(recipe,target)
    review=read(previous/'review-result-v1.json')
    controls={f'legacy-control-{e}-step1000':review['collections'][f'bounded-support-{e}-step1000'] for e in ['raw','EMA']}
    baseline=controls['legacy-control-raw-step1000'];collection=read(baseline['path'])
    save(root/'quality-design-v1.json',{'observations':cases,'endpoints':[f'{a}-{e}-step1000' for a in config['arms'] for e in ['raw','EMA']],
      'new_component_forwards':3288,'new_prediction_arrays':1644,'exact_control_prediction_replays':1644,'new_parent_DINO_forwards':0,'new_noise_draws':0,'scope':config['scope']})
    plan={'root':str(root),'work':str(work),'runner':ref(runner),'config':ref(target),'parent':config['parent'],'previous':str(previous),
      'cache':ref(cache_path),'candidate_cache':ref(data_path),'prefix':cache['batches'][:10],
      'baseline_training':ref(previous/'train-result-v1.json'),'baseline_collection':baseline,'baseline_export':collection['export'],'control_collections':controls,
      'pair_unit_table':config['pair_unit_table'],'candidate_pair_unit_table':ref(unit_path),
      'external_root':str(external),'external_quality_root':str(external),
      'quality_output_roots':{f'{a}-{e}-step1000':str((root if a=='legacy-control' else external)/'review-v1') for a in config['arms'] for e in ['raw','EMA']},
      'expected_new_quality_bytes_external':2*per_endpoint,'expected_new_quality_bytes_per_endpoint':per_endpoint,
      'new_parent_DINO_forwards':0,'new_noise_draws':0,'source_modules':90,
      'inputs':[ref(recipe),ref(target),shared,ref(previous/'plan-v1.json'),ref(cache_path),ref(data_path),ref(root/'data-parent-flag-validation-v1.json'),
        ref(root/'data-actual-viewing-v1.json'),ref(unit_path),config['pair_unit_table'],ref(previous/'train-result-v1.json'),ref(root/'quality-design-v1.json'),baseline,collection['export'],*controls.values()],
      'frozen_files':{str(p):ref(p)['sha256'] for p in work.rglob('*') if p.is_file()},'scope':config['scope']}
    assert len(list((work/'src/demosaic').glob('*.py')))==90
    for p,h in data_plan['all90_neural_hashes'].items():assert ref(work/'src/demosaic'/Path(p).name)['sha256']==h
    save(root/'plan-v1.json',plan);guard(plan);return root/'plan-v1.json'


def classes():
    from demosaic.late_bounded_support import LateBoundedSupportDetail
    return {"legacy-control":LateBoundedSupportDetail,"fine-mesh":LateBoundedSupportDetail}


def equal_tree(first, second):
    import torch

    if isinstance(first, torch.Tensor):
        return isinstance(second, torch.Tensor) and torch.equal(first.cpu(), second.cpu())
    if isinstance(first, dict):
        return first.keys() == second.keys() and all(
            equal_tree(v, second[k]) for k, v in first.items()
        )
    if isinstance(first, (list, tuple)):
        return (
            type(first) is type(second)
            and len(first) == len(second)
            and all(equal_tree(a, b) for a, b in zip(first, second, strict=True))
        )
    return first == second


def runtime(plan):
    import torch

    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.cuda.set_per_process_memory_fraction(
        12 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    assert psutil.virtual_memory().available > 52 * 2**30


def resource_check(root):
    resources = {
        "RAM_available_bytes": psutil.virtual_memory().available,
        "local_free_bytes": shutil.disk_usage(root).free,
        "external_free_bytes": shutil.disk_usage("/mnt/external").free,
    }
    assert (
        resources["RAM_available_bytes"] > 32 * 2**30
        and resources["local_free_bytes"] > 56 * 2**30
        and resources["external_free_bytes"] > 116 * 2**30
    ), resources


def fit(plan, phase):
    import numpy as np
    import torch
    import yaml
    from flat_target_anchor import flat_target_anchor_loss, flat_target_mask
    from local_excess_risk import local_excess_risk
    from noisy_objective import ADC_only, apply_ADC_weight
    from paired_response_objective import paired_response_loss
    from paired_common_objective import paired_common_error_loss
    from paired_common_routing import common_output_with_fixed_support
    from regional_dc_objective import regional_dc_excess
    from robust_spectral_objective import spectral_loss

    from demosaic.prediction_archive import fingerprint

    root = Path(plan["root"])
    config = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    recipe = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    counts = {label: 0 for label in recipe["arms"]}
    updates = dict(counts)
    supervised = dict(counts)
    zero_ADC = dict(counts)
    peak_evaluations = dict(counts)
    LIVE_PROGRESS.update(phase=phase, counts=counts, updates=updates, last_completed_step=0)

    module_configs = {k: {"max_window":256,"support_floor":.25} for k in recipe["arms"]}

    def fresh():
        modules = {k: classes()[k](**module_configs[k]).cuda() for k in recipe["arms"]}
        assert modules["fine-mesh"].support_floor == .25
        for name, value in modules["legacy-control"].state_dict().items():
            assert all(torch.equal(value, m.state_dict()[name]) for m in modules.values())
        assert all(m.relative_in.weight.count_nonzero() == 0 for m in modules.values())
        assert modules["fine-mesh"].harmonic_in.weight.count_nonzero() == 0
        for label, m in modules.items():
            assert (
                sum(p.numel() for p in m.parameters()) == recipe["arms"][label]["parameters"]
                and len(m.state_dict()) == recipe["arms"][label]["parameter_tensors"]
            )
            m.register_forward_hook(
                lambda *args, label=label: counts.__setitem__(label, counts[label] + 1)
            )
        opts = {k: torch.optim.AdamW(m.parameters(), lr=config["lr"]) for k, m in modules.items()}
        emas = {
            k: {n: v.detach().clone() for n, v in m.state_dict().items()}
            for k, m in modules.items()
        }
        return modules, opts, emas

    modules, optimizers, emas = fresh()
    maximum = {k: {n: 0.0 for n, _ in m.named_parameters()} for k, m in modules.items()}
    cache_rows = read(plan["cache"]["path"])["batches"]
    candidate_rows = read(plan["candidate_cache"]["path"])["batches"]
    candidate_units = read(plan["candidate_pair_unit_table"]["path"])["rows"]
    reference_trace = read(plan["baseline_training"]["path"])["trace"]
    unit_rows = read(plan["pair_unit_table"]["path"])["rows"]
    compatible_steps = 0
    smoke_trace = read(root / "smoke-result-v1.json")["trace"] if phase == "train" else None
    checkpointdir = root / "checkpoints"
    checkpointdir.mkdir(exist_ok=True)
    trace = []
    last = 0
    journal = (root / f"{phase}-trace-v1.jsonl").open("x")

    def checkpoint(step):
        dest = checkpointdir / f"{phase}-step{step:04d}.pt"
        assert not dest.exists()
        with dest.open("xb") as stream:
            torch.save(
                {
                    "step": step,
                    "horizon": 1000,
                    "module_config": {"max_window": 256},
                    "module_configs": module_configs,
                    "arms": recipe["arms"],
                    "models": {k: m.state_dict() for k, m in modules.items()},
                    "emas": emas,
                    "optimizers": {k: o.state_dict() for k, o in optimizers.items()},
                    "counts": dict(counts),
                    "updates": dict(updates),
                    "parent": plan["parent"],
                    "plan": ref(root / "plan-v1.json"),
                    "config": config,
                    "torch_CPU_RNG": torch.get_rng_state(),
                    "torch_CUDA_RNG": torch.cuda.get_rng_state(),
                },
                stream,
            )
        return dest

    for step in range(1, 11 if phase == "smoke" else 1001):
        resource_check(root)
        item = cache_rows[step - 1]
        assert ref(item["arrays"]["path"]) == item["arrays"]
        a = dict(np.load(item["arrays"]["path"]))
        assert ref(item["parent"]["path"]) == item["parent"]
        base = np.load(item["parent"]["path"])
        assert fingerprint(base) == item["parent_values"]
        assert {k: fingerprint(v) for k, v in a.items()} == item["inputs"]
        batch = {k: torch.from_numpy(v).cuda() for k, v in a.items()}
        base = torch.from_numpy(base).cuda()
        row = {
            "step": step,
            "batch": item["arrays"],
            "domain": item["metadata"]["domain"],
            "arms": {},
        }
        mask = flat_target_mask(
            batch["target"],
            window=recipe["flat_anchor_window"],
            tolerance_DN16=recipe["flat_anchor_tolerance_DN16"],
        )
        mask_cpu = mask.cpu().numpy()
        row["flat_target_mask"] = {
            "values": fingerprint(mask_cpu),
            "eligible_pixels": int(mask_cpu.sum()),
            "total_pixels": mask_cpu.size,
            "per_image_eligible_pixels": [int(v.sum()) for v in mask_cpu],
        }
        progress = max(0, step - config["warmup"]) / max(1, 1000 - config["warmup"])
        lr = (
            config["lr"]
            * min(1, step / config["warmup"])
            * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
        )
        for label, module in modules.items():
            if label == "fine-mesh":
                del batch,base,a,mask,mask_cpu
                item = candidate_rows[step-1]
                assert ref(item["arrays"]["path"]) == item["arrays"] and ref(item["parent"]["path"]) == item["parent"]
                a = dict(np.load(item["arrays"]["path"]))
                assert {k:fingerprint(v) for k,v in a.items()} == item["inputs"]
                base = np.load(item["parent"]["path"])
                assert fingerprint(base) == item["parent_values"]
                batch = {k:torch.from_numpy(v).cuda() for k,v in a.items()}
                base = torch.from_numpy(base).cuda()
                mask = flat_target_mask(batch["target"],window=recipe["flat_anchor_window"],tolerance_DN16=recipe["flat_anchor_tolerance_DN16"])
                mask_cpu = mask.cpu().numpy()
                row["candidate_batch"] = item["arrays"]
                row["candidate_parent"] = item["parent"]
                row["candidate_flat_target_mask"] = {"values":fingerprint(mask_cpu),"eligible_pixels":int(mask_cpu.sum()),
                    "total_pixels":mask_cpu.size,"per_image_eligible_pixels":[int(v.sum()) for v in mask_cpu]}
            optimizer = optimizers[label]
            optimizer.zero_grad(set_to_none=True)
            for group in optimizer.param_groups:
                group["lr"] = lr
            output, aux = module(
                base, *(batch[k] for k in ("packed", "variance", "colors", "wb")), return_aux=True
            )
            minimum, maximum_support = float(aux["support"].detach().min()), float(aux["support"].detach().max())
            assert recipe["arms"][label]["support_floor"] <= minimum <= maximum_support <= 1
            if step == 1:
                assert torch.all(aux["support"] == .5)
                assert torch.equal(output, base) and aux["correction"].count_nonzero() == 0
            scale = (
                batch["variance"]
                .clamp_min(0)
                .mean((1, 2, 3), keepdim=True)
                .sqrt()
                .clamp_min(recipe["arms"][label]["loss_floor_DN16"] / 65535)
            )
            error = (output - batch["target"]) / scale
            pixel = (error.square() + config["pixel_epsilon_in_noise_units"] ** 2).sqrt().mean()
            derivatives = [error[..., 1:] - error[..., :-1], error[..., 1:, :] - error[..., :-1, :]]
            gradient = (
                sum(
                    (v.square() + config["gradient_epsilon_in_noise_units"] ** 2).sqrt().mean()
                    for v in derivatives
                )
                / 2
            )
            arm = recipe["arms"][label]
            is_ADC = ADC_only(item["metadata"]["noise"])
            peak_bonus = arm["spectral_peak_bonus"] if not is_ADC else 0
            assert peak_bonus == 0
            spectral = spectral_loss(
                module,
                output,
                batch["target"],
                batch["colors"],
                aux,
                arm["loss_floor_DN16"],
                arm["penalty"],
                arm["spectral_epsilon"],
            )
            peak_evaluations[label] += int(peak_bonus > 0)
            loss = config["domain_loss_weights"][row["domain"]] * (
                pixel + config["gradient_weight"] * gradient + config["spectral_weight"] * spectral
            )
            local_penalty = output.new_zeros(())
            if arm["local_risk_weight"]:
                local_penalty = local_excess_risk(
                    output,
                    base,
                    batch["target"],
                    scale,
                    window=recipe["local_risk_window_native"],
                    transition=recipe["local_risk_transition_noise_units"],
                )
                loss = (
                    loss
                    + config["domain_loss_weights"][row["domain"]]
                    * arm["local_risk_weight"]
                    * local_penalty
                )
            dc_penalty = output.new_zeros(())
            if arm["regional_DC_weight"]:
                dc_penalty = regional_dc_excess(
                    output,
                    base,
                    batch["target"],
                    scale,
                    window=recipe["regional_DC_window_native"],
                    transition=arm["regional_DC_transition_units"],
                )
                loss = (
                    loss
                    + config["domain_loss_weights"][row["domain"]]
                    * arm["regional_DC_weight"]
                    * dc_penalty
                )
            pair_scale = batch["pair_units"]
            if arm["pair_unit_floor_DN16"] == 2:
                entry = (unit_rows if label == "legacy-control" else candidate_units)[step - 1]
                assert entry["step"] == step and entry["batch"] == item["arrays"]
                pair_scale = pair_scale.new_tensor(entry["candidate_units_FP32"]).reshape(
                    entry["shape"]
                )
            pair_penalty = output.new_zeros(())
            if arm["paired_response_weight"] and len(batch["pair_indices"]):
                pair_penalty = paired_response_loss(
                    output,
                    batch["target"],
                    pair_scale,
                    batch["pair_indices"],
                    epsilon=recipe["pair_epsilon"],
                )
                loss = (
                    loss
                    + config["domain_loss_weights"][row["domain"]]
                    * arm["paired_response_weight"]
                    * pair_penalty
                )
            anchor_penalty = output.new_zeros(())
            if arm["flat_anchor_weight"]:
                anchor_penalty = flat_target_anchor_loss(
                    output, batch["target"], mask, unit_DN16=recipe["flat_anchor_unit_DN16"]
                )
                loss = (
                    loss
                    + config["domain_loss_weights"][row["domain"]]
                    * arm["flat_anchor_weight"]
                    * anchor_penalty
                )
            common_penalty = output.new_zeros(())
            common_output = output
            if arm["pair_common_weight"] and len(batch["pair_indices"]):
                if arm["common_detach_support"]:
                    common_output = common_output_with_fixed_support(module, output, aux, batch["colors"], batch["wb"])
                    assert torch.equal(common_output.detach().view(torch.int32), output.detach().view(torch.int32))
                common_penalty = paired_common_error_loss(
                    common_output, batch["target"], batch["pair_indices"],
                    unit_DN16=recipe["pair_common_unit_DN16"],
                )
                loss = loss + config["domain_loss_weights"][row["domain"]] * arm["pair_common_weight"] * common_penalty
            loss = apply_ADC_weight(loss, item["metadata"]["noise"], arm["ADC_loss_weight"])
            has_supervision = not (is_ADC and arm["ADC_loss_weight"] == 0)
            supervised[label] += int(has_supervision)
            zero_ADC[label] += int(not has_supervision)
            assert torch.isfinite(loss)
            loss.backward()
            for name, p in module.named_parameters():
                assert p.grad is not None and torch.isfinite(p.grad).all()
                maximum[label][name] = max(maximum[label][name], float(p.grad.abs().max()))
                if not has_supervision:
                    assert p.grad.count_nonzero() == 0
            if not has_supervision:
                assert loss == 0
            norm = torch.nn.utils.clip_grad_norm_(module.parameters(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            updates[label] += 1
            decay = min(config["EMA_decay"], (1 + step) / (10 + step))
            with torch.no_grad():
                for name, value in module.state_dict().items():
                    emas[label][name].lerp_(value, 1 - decay)
            row["arms"][label] = {
                "loss": float(loss.detach()),
                "pixel": float(pixel.detach()),
                "gradient": float(gradient.detach()),
                "spectral": float(spectral.detach()),
                "gradient_norm": float(norm),
                "lr": lr,
                "local_excess_risk": float(local_penalty.detach()),
                "regional_DC_excess": float(dc_penalty.detach()),
                "regional_DC_transition_units": arm["regional_DC_transition_units"],
                "paired_response": float(pair_penalty.detach()),
                "pair_common_error": float(common_penalty.detach()),
                "common_support_detached": bool(arm["common_detach_support"] and len(batch["pair_indices"])),
                "support_mean": float(aux["support"].detach().mean()),
                "support_minimum": minimum,
                "support_maximum": maximum_support,
                "declared_support_floor": arm["support_floor"],
                "spectral_delta_RMS": float(aux["spectral_delta"].detach().abs().square().mean().sqrt()),
                "pair_unit_values": fingerprint(pair_scale.detach().cpu().numpy()),
                "pair_unit_floor_DN16": arm["pair_unit_floor_DN16"],
                "flat_target_anchor": float(anchor_penalty.detach()),
                "coupled_pairs": len(batch["pair_indices"]),
                **(
                    {
                        "spatial_correction_RMS_DN16": float(
                            aux["spatial_correction"].detach().square().mean().sqrt()
                        )
                        * 65535
                    }
                    if "spatial_correction" in aux
                    else {}
                ),
            }
            if label == "legacy-control":
                expected = reference_trace[step - 1]["arms"]["bounded-support"]
                assert {k: row["arms"][label][k] for k in expected} == expected, (
                    phase,
                    step,
                    "V167 bounded control trace",
                )
                compatible_steps += 1
            del (
                output,
                aux,
                error,
                pixel,
                derivatives,
                gradient,
                spectral,
                local_penalty,
                dc_penalty,
                loss,
                scale,
                pair_penalty,
                common_penalty,
                common_output,
                pair_scale,
                anchor_penalty,
            )
        if phase == "train" and step <= 10:
            assert row == smoke_trace[step - 1], (step, "smoke/train prefix continuation")
        trace.append(row)
        journal.write(json.dumps(row, allow_nan=False) + "\n")
        journal.flush()
        LIVE_PROGRESS["last_completed_step"] = step
        last = step
        if step == 1 or step % 10 == 0:
            print(
                json.dumps(
                    {
                        "phase": phase,
                        "step": step,
                        "arms": row["arms"],
                        "CUDA_allocated_bytes": torch.cuda.memory_allocated(),
                    }
                ),
                flush=True,
            )
            save(
                root / f"{phase}-progress-v1.json",
                {"step": step, "counts": counts, "updates": updates},
            )
        del batch, base, a, mask, mask_cpu
        if phase == "smoke" and step == 8:
            path = checkpoint(8)
            s = torch.load(path, map_location="cpu", weights_only=True)
            modules, optimizers, emas = fresh()
            for label in modules:
                modules[label].load_state_dict(s["models"][label], strict=True)
                optimizers[label].load_state_dict(s["optimizers"][label])
                emas[label] = {n: v.cuda() for n, v in s["emas"][label].items()}
                assert len(optimizers[label].state) == recipe["arms"][label][
                    "parameter_tensors"
                ] and all(float(v["step"]) == 8 for v in optimizers[label].state.values())
                assert all(
                    torch.equal(v.cpu(), s["models"][label][n])
                    for n, v in modules[label].state_dict().items()
                )
                assert all(
                    torch.equal(v.cpu(), s["emas"][label][n]) for n, v in emas[label].items()
                )
                reloaded = optimizers[label].state_dict()
                assert reloaded["param_groups"] == s["optimizers"][label]["param_groups"]
                for index, state in reloaded["state"].items():
                    for key, value in state.items():
                        assert torch.equal(value.cpu(), s["optimizers"][label]["state"][index][key])
            torch.set_rng_state(s["torch_CPU_RNG"])
            torch.cuda.set_rng_state(s["torch_CUDA_RNG"])
            assert torch.equal(torch.get_rng_state(), s["torch_CPU_RNG"])
            assert torch.equal(torch.cuda.get_rng_state().cpu(), s["torch_CUDA_RNG"])
            del s
        if phase == "train" and step % 250 == 0:
            checkpoint(step)
    journal.close()
    final = checkpoint(last) if phase == "smoke" else checkpointdir / "train-step1000.pt"
    assert counts == updates == {k: last for k in modules}
    for label, module in modules.items():
        assert (
            min(maximum[label].values()) > 0
            and len(optimizers[label].state) == recipe["arms"][label]["parameter_tensors"]
        )
        assert all(float(v["step"]) == last for v in optimizers[label].state.values())
        assert all(
            torch.isfinite(t).all()
            for state in optimizers[label].state.values()
            for t in state.values()
        )
        assert all(
            torch.isfinite(v).all() for v in [*module.state_dict().values(), *emas[label].values()]
        )
    expected_ADC = sum(ADC_only(x["metadata"]["noise"]) for x in cache_rows[:last])
    assert supervised == {
        k: last - (expected_ADC if v["ADC_loss_weight"] == 0 else 0)
        for k, v in recipe["arms"].items()
    }
    assert zero_ADC == {
        k: (expected_ADC if v["ADC_loss_weight"] == 0 else 0) for k, v in recipe["arms"].items()
    }
    assert peak_evaluations == {
        k: (last - expected_ADC if v["spectral_peak_bonus"] else 0)
        for k, v in recipe["arms"].items()
    }
    if phase == "train":
        previous = read(plan["baseline_training"]["path"])
        assert ref(previous["checkpoint"]["path"]) == previous["checkpoint"]
        saved = torch.load(previous["checkpoint"]["path"], map_location="cpu", weights_only=True)
        assert equal_tree(modules["legacy-control"].state_dict(), saved["models"]["bounded-support"])
        assert equal_tree(emas["legacy-control"], saved["emas"]["bounded-support"])
        assert equal_tree(
            optimizers["legacy-control"].state_dict(), saved["optimizers"]["bounded-support"]
        )
        del saved
    guard(plan)
    save(
        root / f"{phase}-result-v1.json",
        {
            "status": "completed-matched-head-phase",
            "phase": phase,
            "steps": last,
            "plan": ref(root / "plan-v1.json"),
            "checkpoint": ref(final),
            "counts": counts,
            "updates": updates,
            "supervised_batches": supervised,
            "zero_ADC_gradient_batches": zero_ADC,
            "peak_weight_evaluations": peak_evaluations,
            "parameter_maximum_gradients": maximum,
            "loss_floors_DN16": {k: v["loss_floor_DN16"] for k, v in recipe["arms"].items()},
            "initial_outputs_exact_parent": True,
            "trace": trace,
            "exact_V167_control_trace_rows": compatible_steps,
            "control_final_raw_EMA_Adam_exact": phase == "train",
            "head_image_evaluations": 8 * last,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": recipe["scope"],
        },
    )


def worker(path, phase):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert ref(__file__) == plan["runner"]
    (root / f"{phase}.claim").open("x").close()
    runtime(plan)
    try:
        fit(plan, phase)
    except BaseException as error:
        save(
            root / f"{phase}-failure-v1.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "progress": LIVE_PROGRESS,
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            },
        )
        raise


def controller(path):
    plan = read(path)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None
    try:
        for phase in ("smoke", "train"):
            guard(plan)
            while psutil.virtual_memory().available < 52 * 2**30:
                save(
                    root / "status-v1.json",
                    {**state, "status": "waiting-for-headroom", "phase": phase},
                )
                time.sleep(2)
            env = dict(
                os.environ,
                PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
                OMP_NUM_THREADS="2",
                OPENBLAS_NUM_THREADS="1",
                MKL_NUM_THREADS="1",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                CUDA_VISIBLE_DEVICES="0",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
            )
            with (root / f"{phase}-v1.log").open("x") as log:
                child = subprocess.Popen(
                    [
                        str(REPO / ".venv/bin/python"),
                        "-P",
                        plan["runner"]["path"],
                        "worker",
                        str(path),
                        "--phase",
                        phase,
                    ],
                    cwd=plan["work"],
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                save(
                    root / "status-v1.json",
                    {**state, "status": "running-declared-phase", "phase": phase, "child": owner},
                )
                observed = 0.0
                last = time.monotonic()
                while child.poll() is None:
                    time.sleep(2)
                    now = time.monotonic()
                    if live(owner) and psutil.Process(child.pid).status() != psutil.STATUS_STOPPED:
                        observed += min(now - last, 5.0)
                    last = now
                    assert observed < (1800 if phase in ("parity", "smoke") else 7200), phase
                assert child.returncode == 0, phase
            assert not live(owner)
            state["completed"][phase] = ref(root / f"{phase}-result-v1.json")
        save(
            root / "status-v1.json",
            {**state, "status": "completed-matched-training-awaiting-fixed-quality-review"},
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGTERM)
            child.wait(timeout=30)
        save(
            root / "status-v1.json",
            {**state, "status": "failed-preserved-no-automatic-retry", "error": repr(error)},
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("smoke", "train"))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path))
    elif args.mode == "worker":
        worker(args.path.resolve(), args.phase)
    else:
        controller(args.path.resolve())
