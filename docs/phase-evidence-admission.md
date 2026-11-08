# V178 CUDA admission queued after V175

The [V178 model variant](phase-evidence-matching.md) has completed CPU
preparation. Its separate CUDA admission is now frozen and queued behind the
complete V175 training/review/render pipeline. **No V178 GPU work, admission
update or trained-quality result is claimed in this preparation.** The CPU
watcher is live; current restoration recommendations remain unchanged.

[Worker and watcher](../scripts/admit_phase_evidence_matching.py) ·
[Dependency protocol](../scripts/phase_admission_protocol.py) ·
[Protocol tests](../tests/test_phase_admission_protocol.py) ·
[Source/input/launch/readiness receipt](results/v178-CUDA-admission-preparation-v1.json).

## Fixed GPU check

Seven native cached cases supply four noisy training domains (mesh, photo,
mixed, flat), one ADC-only training batch, the protected main sky and the
nominal fine cab mesh. Both existing V172 endpoints are loaded as compatibility
controls; this does not choose the initializer of a future quality trial.
Cached V143 outputs provide the parents. No new V143/DINO inference, sensor
noise, source geometry, RAW decode or original-photo access is needed.

The planned sequence is:

1. Compare old/new initial RGB outputs bit-for-bit on all seven cases at raw
   and EMA weights: 14 comparisons, 28 component forwards. For the 12 noisy new
   forwards, check the measured feature maps/bins against CPU FP32 extraction.
2. Starting again from the raw weights and a fresh optimizer, run one real
   native 512 mesh update with the unchanged seven-term objective. Check finite
   gradients on all 142 trainable tensors, including nonzero adapter gradients,
   and absence of gradients/changes in the frozen component.
3. Save and genuinely restore model, all Adam moments/steps and CPU/CUDA RNG in
   a newly constructed module. Run the second update on the existing mixed
   batch, continuing at Adam step 2 without replaying update 1.
4. After those updates, check exact ADC bypass and exact frozen output in
   artificially zero-conditioned cells. Separately check zero evidence maps
   for constant phases and unchanged A-selection when only B is changed.

The conditioning checks are mathematical fixtures, not physical captures or
evidence that a noisy sky is safe. These two optimizer updates are admission
probes, not a trained model or quality evaluation. No admission checkpoint is
promoted or automatically used to start training.

Expected actual component totals are **32 wrapper/frozen calls, 27 matching
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
An actual call to the frozen worker entry intentionally rejects the current
live V175 owner **before Torch import**, leaving no admission launch/claim or
scientific failure record. Subsequent CPU-only import/constructor checks verify
the actual frozen dependencies, 142 trainable tensors, five sampler blocks and
the 3,120-weight zero adapter; CUDA is not initialized.

The waiting process has been observed live with about 20 MiB RSS and no loaded
Torch/CUDA libraries, while V175 and its completion watcher retain their
original live owners. Human native viewing/report publication for V175 can
follow its render while the separate admission runs. V178 still needs inspection
of actual admission results, a training trial and full numerical/native quality
comparisons before any detail or flat-region improvement can be claimed.
