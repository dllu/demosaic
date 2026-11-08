# V178 CUDA admission completed

The [V178 model variant](phase-evidence-matching.md) passes its actual CUDA
admission after V175's completed training/review/render pipeline. All 14 initial
old/new RGB comparisons are bit-exact. Both probe updates have finite, nonzero
gradients on all 142 trainable tensors, including all 3,120 adapter weights;
model/Adam/CPU-CUDA RNG restoration and post-update ADC invariants pass.
**This is execution validation; V178 image quality remains unmeasured.** The
[matched continuation](phase-evidence-training.md) is now running from the
original V172 history. Current restoration recommendations remain unchanged.

[Worker and watcher](../scripts/admit_phase_evidence_matching.py) ·
[Dependency protocol](../scripts/phase_admission_protocol.py) ·
[Protocol tests](../tests/test_phase_admission_protocol.py) ·
[Source/input/launch/readiness receipt](results/v178-CUDA-admission-preparation-v1.json).

[Completed admission, journals, restore and CPU checkpoint inspection](results/v178-CUDA-admission-completed-v1.json).

## Actual numerical and resource checks

The 12 noisy new-model parity forwards expose captured GPU feature fields for
comparison with six CPU references. Both endpoints select the same bins as CPU.
All **170,393,600 feature coordinates** pass the fixed 1e−4 absolute/relative
tolerance, counting the same inputs separately at raw and EMA weights.
There are 85,196,800 coordinates per endpoint, not that many independent images.

| Cached case | Feature coordinates per endpoint | Maximum CPU/GPU absolute difference |
|---|---:|---:|
| Training mesh, step 1 | 20,971,520 | 6.78e−7 |
| Training photo, step 2 | 5,242,880 | 6.43e−7 |
| Training mixed, step 4 | 20,971,520 | 1.67e−6 |
| Training flat, step 8 | 20,971,520 | 7.15e−7 |
| Main overcast sky | 5,242,880 | 5.36e−7 |
| Fine cab mesh | 11,796,480 | 2.00e−6 |

ADC-only parity bypasses feature extraction. The six listed differences are
identical across the two endpoint comparisons. The two fresh-Adam admission
checkpoints have 142 states at steps 1 and 2; they do not inherit V172's 900
updates. The actual trial separately restores that history. All 47 frozen
tensors stay exact, with no replay of the first probe update.

Peak allocated CUDA memory is **6.27 GiB** on GB10. The run uses the existing
pinned sampler binary, makes no new V143/DINO, noise/source or RAW-decoder calls,
and never uses protected captures in an optimizer update. The CPU inspection
checks both actual checkpoint files and admission records without new inference.
Constant-map and zero-conditioned-cell checks do not establish noisy-sky safety.

## Fixed GPU check

Seven native cached cases supply four noisy training domains (mesh, photo,
mixed, flat), one ADC-only training batch, the protected main sky and the
nominal fine cab mesh. Both existing V172 endpoints are loaded as compatibility
controls; the matched trial's initializer is specified separately.
Cached V143 outputs provide the parents. No new V143/DINO inference, sensor
noise, source geometry, RAW decode or original-photo access is needed.

The completed sequence was:

1. Compared old/new initial RGB outputs bit-for-bit on all seven cases at raw
   and EMA weights: 14 comparisons, 28 component forwards. For the 12 noisy new
   forwards, checked measured feature maps/bins against CPU FP32 extraction.
2. Starting again from the raw weights and a fresh optimizer, ran one real
   native 512 mesh update with the unchanged seven-term objective. Checked finite
   gradients on all 142 trainable tensors, including nonzero adapter gradients,
   and absence of gradients/changes in the frozen component.
3. Saved and genuinely restored model, all Adam moments/steps and CPU/CUDA RNG in
   a newly constructed module. Ran the second update on the existing mixed
   batch, continuing at Adam step 2 without replaying update 1.
4. After those updates, checked exact ADC bypass and exact frozen output in
   artificially zero-conditioned cells. Separately checked zero evidence maps
   for constant phases and unchanged A-selection when only B is changed.

The conditioning checks are mathematical fixtures, not physical captures or
evidence that a noisy sky is safe. These two optimizer updates are admission
probes, not a trained model or quality evaluation. No admission checkpoint is
promoted or automatically used to start training.

Actual component totals are **32 wrapper/frozen calls, 27 matching
calls and 135 sampler calls**; the new evidence projection runs 15 times. Six
CPU feature calls and three direct CUDA feature checks are separate. Two
checkpoint files retain the actual update/restore evidence. Every component
entry and completed parity/update row is journaled; failures stop without
automatic retry or successful-prefix replay.

## Launch proof

The watcher requires all three V175 owners—training, review and completion
watch—to be terminal by matching PID **and process creation time**. Completed
result records must bind to those same owners. Missing processes alone do not
prove success. The final watcher state and completed training/quality/offset
audits, paired reduction and native render must also exist. A live owner wins
over a prematurely written completion record. Permission/transient observation
errors keep waiting; dependency failures stop for inspection.

Both watcher and worker check this proof. The worker checks it before importing
Torch, initializing CUDA or creating its scientific claim. Frozen code, cached
inputs, parent outputs, checkpoint and native sampler library are bound by
hashes. Separate worker/watcher status files preserve owner identity. The worker
loads the existing pinned sampler binary, without a new native build.

Runtime minimums remain 32 GiB RAM/48 GiB local/111 GiB external, with 52 GiB launch
RAM and 24 GiB per-process CUDA quota. Launch also reserves 0.2 GiB new output
space plus 0.5 GiB margin on both disks. Preparation separately accounts for
V175's existing forecasts; no V175 reserve, source or recipe is changed. Both
processes use CPU cores 4/5 at nice 10. No other process is killed or changed.

The new 18 CPU protocol tests pass, covering live/completed owners, PID reuse,
missing launches/results, incorrect owners, dependency failures, incomplete
rendering, denied observations and the actual offset-audit status spelling.
During preparation, an actual call to the frozen worker entry intentionally
rejected the then-live V175 owner **before Torch import**, leaving no admission
launch/claim or scientific failure record. CPU-only import/constructor checks verified
the actual frozen dependencies, 142 trainable tensors, five sampler blocks and
the 3,120-weight zero adapter; CUDA is not initialized.

The waiting process was observed with about 20 MiB RSS and no loaded Torch/CUDA
libraries while V175 was live. It launched admission only after the original
training, review and completion-watch owners exited with completed receipts.
The admission worker and watcher are now terminal, and the separate trial
controller has inspected the actual admission checkpoints. V178 still needs
completed matched training, numerical/native quality comparisons and actual
viewing before any detail or flat-region improvement can be claimed.
