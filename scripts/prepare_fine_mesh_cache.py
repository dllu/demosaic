"""Inspect once and cache the selected fine-mesh data with a frozen V143 parent."""

import argparse
import json
import os
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from fine_mesh_training_data import edited_observation
from paired_response_counters import count_source_draws
from train_directional_bank_trial import guard, read, ref, save

from demosaic.prediction_archive import fingerprint


def resources(plan, remaining):
    reserves = plan["reserves_GiB"]
    assert shutil.disk_usage(plan["root"]).free > (
        reserves["local"] + reserves["projection_margin"] + reserves["local_remaining_bound"]
    ) * 2**30
    assert shutil.disk_usage(plan["external_root"]).free > (
        reserves["external"] + reserves["projection_margin"]
    ) * 2**30 + remaining + plan["expected_later_new_quality_bytes"]
    assert psutil.virtual_memory().available > plan["runtime_RAM_GiB"] * 2**30


def construct(item, selected):
    assert ref(item["arrays"]["path"]) == item["arrays"]
    old = dict(np.load(item["arrays"]["path"]))
    assert {k: fingerprint(v) for k, v in old.items()} == item["inputs"]
    before = torch.get_rng_state().clone()
    with count_source_draws() as draws:
        arrays, metadata = edited_observation(item, old, selected["mesh_ordinal"])
    assert draws == {"sensor_Poisson": 3, "sensor_Gaussian": 1,
                     "procedural_Poisson": 0, "procedural_Gaussian": 0,
                     "coupled_sensor_calls": 1, "ordinary_sensor_calls": 0}
    assert torch.equal(before, torch.get_rng_state())
    # Independently recover clean Bayer samples from saved camera-RGB targets.
    clean = [np.stack([np.stack([rgb[int(c), k//2::2, k%2::2] for k,c in enumerate(colors)])
                       for rgb,colors in zip(arrays["target"][p::2],arrays["colors"][p::2],strict=True)])
             for p in (0,1)]
    assert fingerprint(clean[0]) == metadata["sensor"]["clean_packed_a"]
    assert fingerprint(clean[1]) == metadata["sensor"]["clean_packed_b"]
    for pair in range(2):
        empty = clean[0][pair] == clean[1][pair]
        assert np.array_equal(arrays["packed"][2*pair][empty], arrays["packed"][2*pair+1][empty])
    metadata["actual_sampler_calls"] = draws
    return arrays, metadata, old


def input_record(root, plan, item, selected):
    arrays, metadata, old = construct(item, selected)
    path = Path(plan["external_root"]) / "training-batches" / f"step-{item['step']:04d}-inputs.npz"
    assert not path.exists()
    with path.open("xb") as stream:
        np.savez(stream, **arrays)
    record = {"step": item["step"], "arrays": ref(path), "metadata": metadata,
              "inputs": {k: fingerprint(v) for k,v in arrays.items()},
              "legacy_arrays": item["arrays"], "mesh_ordinal": selected["mesh_ordinal"]}
    return arrays, old, record


def inspect(root, plan, cache):
    from PIL import Image, ImageDraw, ImageFont
    from demosaic.archive_metrics import noisy_malvar
    selected = {r["step"]: r for r in plan["selected"]}
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    records, figures = [], []
    image_dir = root / "data-inspection-v1"
    image_dir.mkdir()
    for step in plan["inspection_steps"]:
        resources(plan, plan["expected_new_cache_bytes"])
        a, old, record = input_record(root, plan, cache["batches"][step-1], selected[step])
        noisy = noisy_malvar(a)
        board = Image.new("RGB", (4*168, 2*212), "white")
        draw = ImageDraw.Draw(board)
        panels = []
        for pair in range(2):
            index = 2*pair
            x,y,w,h = (176,176,160,160)
            anchor = a["target"][index+1,:,y:y+h,x:x+w].mean((1,2),dtype=np.float64)
            def display(value):
                v = value[:,y:y+h,x:x+w].astype(np.float64)
                v = anchor[:,None,None] + 8*(v-anchor[:,None,None])
                rgb = np.einsum("ij,jhw->ihw",a["matrix"][index].astype(np.float64),
                                v*8*a["wb"][index,:,None,None].astype(np.float64)).clip(0,1)
                rgb = np.where(rgb <= .0031308, 12.92*rgb, 1.055*rgb**(1/2.4)-.055)
                return np.rint(rgb.transpose(1,2,0)*255).astype(np.uint8)
            values = [("Legacy clean",old["target"][index]),("Fine clean",a["target"][index]),
                      ("Fine noisy Malvar",noisy[index]),("Exact empty",a["target"][index+1])]
            source = record["metadata"]["cases"][index]["source"]
            recipe = source["present_recipe"]
            draw.text((4,pair*212+3),f"step{step}/pair{pair},band{recipe['contrast_band']},contrast{recipe['requested_peak_relative_contrast']:.5f};8x display contrast/exposure8",fill="black",font=font)
            for column,(label,value) in enumerate(values):
                draw.text((column*168+4,pair*212+22),label,fill="black",font=font)
                board.paste(Image.fromarray(display(value)),(column*168+4,pair*212+43))
            panels.append({"pair":pair,"ROI_xywh":[x,y,w,h],"exposure":8,"contrast":8,
                           "anchor_camera_RGB":anchor.tolist(),"nominal_periods":recipe["periods_final_pixels"],
                           "contrast_band":recipe["contrast_band"],"requested_peak_relative_contrast":recipe["requested_peak_relative_contrast"]})
        image_path = image_dir / f"step-{step:04d}.png"
        board.save(image_path)
        records.append(record)
        figures.append({"image":ref(image_path),"step":step,"panels":panels,"no_resize":True})
    guard(plan)
    save(root/"data-inspection-v1.json",{"status":"completed-six-original-input-constructions-awaiting-actual-viewing",
         "plan":ref(root/"data-plan-v1.json"),"batches":records,"figures":figures,
         "source":dict(ref(Path(__file__)),text=Path(__file__).read_text()),
         "actual_new_source_renders":24,"actual_geometry_transforms":24,"Poisson_calls":18,"Gaussian_calls":6,
         "parent_root_calls":0,"DINO_calls":0,"neural_head_calls":0,"scope":plan["scope"]})
    print("Inspected6 original inputs/12 pairs;18 Poisson/6 Gaussian;no neural calls;actual viewing pending",flush=True)


def cache_parent(root, plan, old_cache):
    from profile_raw_kernel_inference import model_hash
    from demosaic.inference import load_checkpoint
    viewed = read(root/"data-actual-viewing-v1.json")
    assert viewed["status"] == "actually-viewed-all-six-data-boards-at-original-detail"
    assert viewed["inspection"] == ref(root/"data-inspection-v1.json")
    inspection = read(viewed["inspection"]["path"])
    adopted = {r["step"]:r for r in inspection["batches"]}
    selected = {r["step"]:r for r in plan["selected"]}
    resources(plan,plan["expected_new_cache_bytes"])
    assert psutil.virtual_memory().available > plan["launch_RAM_GiB"]*2**30
    with torch.random.fork_rng(devices=[0]):
        parent,loaded = load_checkpoint(plan["parent"]["path"],"cuda")
    assert loaded["loaded_sha256"] == plan["parent"]["sha256"]
    parent.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    before,backbone = model_hash(parent),model_hash(parent.context.backbone)
    assert before == old_cache["parent_before"] == old_cache["parent_after"]
    assert backbone == plan["expected_DINO_sha256"]
    counts = {"parent_entered":0,"parent_returned":0,"DINO_entered":0,"DINO_returned":0}
    for model,prefix in [(parent,"parent"),(parent.context.backbone,"DINO")]:
        model.register_forward_pre_hook(lambda *args,prefix=prefix:counts.__setitem__(prefix+"_entered",counts[prefix+"_entered"]+1))
        model.register_forward_hook(lambda *args,prefix=prefix:counts.__setitem__(prefix+"_returned",counts[prefix+"_returned"]+1))
    cpu_rng,cuda_rng = torch.get_rng_state().clone(),torch.cuda.get_rng_state().clone()
    remaining = plan["expected_new_cache_bytes"]-sum(Path(r["arrays"]["path"]).stat().st_size for r in adopted.values())
    rows=[];new_sources=0
    with (root/"data-cache-trace-v1.jsonl").open("x") as journal, (root/"data-parent-forward-events-v1.jsonl").open("x") as forward:
        for item in old_cache["batches"]:
            step=item["step"]
            if step not in selected:
                rows.append(item)
                continue
            resources(plan,remaining)
            if step in adopted:
                record=adopted[step];assert ref(record["arrays"]["path"])==record["arrays"]
                a=dict(np.load(record["arrays"]["path"]));assert {k:fingerprint(v) for k,v in a.items()}==record["inputs"]
            else:
                a,old,record=input_record(root,plan,item,selected[step]);del old
                new_sources+=1;remaining-=Path(record["arrays"]["path"]).stat().st_size
            tensors={k:torch.from_numpy(a[k]).cuda() for k in ["packed","variance","colors","wb","matrix"]}
            noise=record["metadata"]["noise"];parent.set_noise(noise["shot"],noise["read"])
            forward.write(json.dumps({"step":step,"event":"before-parent","counts":dict(counts)})+"\n");forward.flush()
            with torch.inference_mode():
                base=parent(*(tensors[k] for k in ["packed","variance","colors","wb","matrix"])).cpu().numpy()
            forward.write(json.dumps({"step":step,"event":"returned-parent","counts":dict(counts),"images":4})+"\n");forward.flush()
            assert base.shape==a["target"].shape and np.isfinite(base).all()
            path=Path(plan["external_root"])/"training-batches"/f"step-{step:04d}-parent.npy"
            with path.open("xb") as stream:np.save(stream,base,allow_pickle=False)
            remaining-=path.stat().st_size
            complete=dict(record,parent=ref(path),parent_values=fingerprint(base),inspection_input_adopted=step in adopted)
            rows.append(complete);journal.write(json.dumps(complete,allow_nan=False)+"\n");journal.flush()
            assert torch.equal(cpu_rng,torch.get_rng_state()) and torch.equal(cuda_rng,torch.cuda.get_rng_state())
            assert torch.cuda.max_memory_allocated() < plan["CUDA_quota_GiB"]*2**30
            save(root/"data-cache-progress-v1.json",{"last_step":step,"counts":dict(counts),"fresh_input_batches":new_sources,"remaining_new_cache_bytes":remaining})
            if counts["parent_returned"]%10==0 or counts["parent_returned"]==1:print(dict(step=step,counts=dict(counts)),flush=True)
            del a,tensors,base
    assert len(rows)==1000 and len(selected)==171 and new_sources==165
    assert all(v==171 for v in counts.values()) and abs(remaining)<16384
    assert model_hash(parent)==before and model_hash(parent.context.backbone)==backbone
    assert all(not p.requires_grad and p.grad is None for p in parent.parameters())
    guard(plan)
    save(root/"data-cache-result-v1.json",{"status":"completed171-new-frozen-parent-batches-and829-exact-legacy-adoptions",
         "plan":ref(root/"data-plan-v1.json"),"batches":rows,"counts":counts,"new_parent_images":684,"new_DINO_images":684,
         "parent_before":before,"parent_after":model_hash(parent),"DINO_before":backbone,"DINO_after":model_hash(parent.context.backbone),
         "adopted_legacy_batches":829,"new_input_batches":171,"inspection_inputs_adopted":6,"additional_input_constructions":165,
         "actual_total_input_source_renders":684,"actual_total_geometry_transforms":684,"actual_total_Poisson_calls":513,"actual_total_Gaussian_calls":171,
         "global_Torch_RNG_unchanged":True,"CUDA_peak_allocated_bytes":torch.cuda.max_memory_allocated(),
         "owner":{"pid":os.getpid(),"created":psutil.Process().create_time()},
         "source":dict(ref(Path(__file__)),text=Path(__file__).read_text()),"scope":plan["scope"]})
    print("PASS171 new parent/DINO roots;6 inspected inputs adopted;829 legacy arrays/parents reused",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root",type=Path);parser.add_argument("phase",choices=["inspect","cache"])
    args=parser.parse_args();root=args.root.resolve();plan=read(root/"data-plan-v1.json");guard(plan)
    binding=read(root/"data-worker-source-v1.json");assert ref(Path(__file__))==binding["worker"]
    (root/f"data-{args.phase}.claim").open("x").close()
    os.nice(10);os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest");torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
    (Path(plan["external_root"])/"training-batches").mkdir(exist_ok=True)
    old_cache=read(plan["cache"]["path"])
    owner={"pid":os.getpid(),"created":psutil.Process().create_time()}
    save(root/f"data-{args.phase}-owner-v1.json",owner)
    try:
        (inspect if args.phase=="inspect" else cache_parent)(root,plan,old_cache)
    except BaseException as error:
        save(root/f"data-{args.phase}-failure-v1.json",{"status":"failed-preserved-no-automatic-retry","owner":owner,"error":repr(error)})
        raise


if __name__=="__main__":main()
