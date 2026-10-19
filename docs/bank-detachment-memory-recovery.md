# Bank-gradient study: recovery from the memory guard

The detached V83 arm stopped at the system-memory guard before update 3,000.
It saved a genuine, finite emergency checkpoint at **step 2,999**. The connected
V82 arm had already completed its original 4,000 updates. A separately frozen
recovery completed the detached checkpoint's original 4,000-update boundary.
The complete quality review is now running; its conclusions remain pending.
[Diagnosed failure, state checks, actual replay and rebound review receipt](results/bank-detachment-memory-recovery-v1.json).
[Completed 4,000-step boundary and independent CPU audit](results/bank-detachment-recovered4000-completion-v1.json).

The trainer reported only 6.7 GB of available system memory. The separate
Commons preparer also stopped at its 24 GiB memory guard. These are recorded
controlled guard exits, without a recorded nonfinite-model failure. The
available evidence does not establish which shared-machine workload caused
the pressure. No other project's processes were stopped. The old controllers,
logs, failed status receipts, checkpoints and partial caches remain intact.

The emergency checkpoint contains finite values in all 105 model tensors,
105 EMA tensors and 103 AdamW states, with optimizer step 2,999. Its immutable
recovery copy has SHA-256
`a2d8ba8748be604595eea26064f92ee4769773c1bc23fba4bf4ed0e059f9eca1`.
The completed connected checkpoint is retained without retraining.

The [recovery adapter](../scripts/recover_bank_detachment.py) uses the archived
trainer and its original completion checks. All 44 training-core package files
remain byte-for-byte identical. It restores optimizer, EMA and Python/CPU/CUDA
RNG states, uses the original per-step data seeds, and performs exactly the
remaining 1,001 updates. Data membership, model, noise, losses, seed, batch size,
precision, original cosine horizon and the
[predeclared quality criteria](directional-bank-detachment-v82-v83.md) are unchanged.
The active-time timeout retains the unused portion of the original arm budget.

Before production, an actual CPU fixture exercised the same low-memory guard:
an emergency checkpoint at step 3 exactly preserved the saved model, EMA,
optimizer, RNG and best-monitor state. Resuming it through step 6 matched the
model, EMA, optimizer and all RNG states bitwise against an uninterrupted
six-update reference. The unchanged quality-review boundary reader also accepted
this genuine recovered fixture. These checks establish recovery behavior,
without providing model-quality evidence.

Production waited for at least 48 GiB of available RAM for 60 continuous seconds.
One discarded CUDA update from the genuine parent reproduced the original
initial model, first output and raw gradient hashes. This reconstructs the
original worker's initialization evidence; its weights do not enter the resumed
trajectory. Before the resumed first forward, all saved model tensors exactly
matched the step-2,999 checkpoint. Sampled input and target hashes were checked
against the connected arm before the corresponding resumed update. The initial
receipt records step 3,575; the subsequent independent completion audit verifies
the actual final checkpoints at step 4,000. Both have finite 105 model/105 EMA/
103 AdamW states and optimizer step 4,000. All 176 sampled input/target pairs,
161 logged domain/LR pairs and final Python/CPU/CUDA RNG states match between
arms. All 135 pre-interruption sample rows and 248 frozen files are preserved.
The audit exited successfully with CUDA uninitialized.

The same ten-stage photo, analytic, camera, color and native-pixel review is
bound to the new recovery controller's exact PID and creation time. Separate
CPU closure and reference followers wait for its successful completion. The
first quality stage has started after the training owner's successful exit. The
review retains exact-GT native crop triplets and the cached GFX sky, building,
foliage, fence and lights comparisons, with accurate independent-reference
labels. Actual viewing and all original gates remain required before any
quality conclusion. V43 and the README examples remain unchanged.

A [source-bound report-assets queue](results/bank-detachment-report-assets-queue-v1.json)
now waits for all three exact review/closure/reference owners to exit. Its
actual historical CPU preflight verifies 125 native cells, 81 source triplets,
eight boards and 12 selected triplets without Torch or inference. Production
will include two exact-GT triplets per checkpoint and all four standing GFX
regions, with identical pixels and complete source/ROI/noise/exposure/reference
metadata. Historical replay is not evidence about the current models. Packaging
retains `manual_review_completed: false` until the actual boards are viewed.

Current operational roots:

- Training: `.cache/experiments/bank-detachment-v82-v83-memory-recovery-v1/`.
- Review: `.cache/experiments/bank-detachment-v82-v83-memory-recovery-review-v1/`.
- Closure: `.cache/experiments/bank-detachment-v82-v83-memory-recovery-native-closure-v1/`.

Check their current status, logs and actual PID/creation identities before
acting. The published receipt is a dated observation, not proof of later
liveness or completion. A new failure stops this recovery without automatic
retry or a training extension.

The local Commons downloader completed all 1,188 originals before the memory
stop. Its preparer retained partial atomic caches, but did not finish; the
dependent archive handoff exited before reconciliation or broader downloading.
New [cache-recovery and archive-handoff plans](commons-local-memory-recovery.md)
wait for GPU review and CPU closure before reusing retained valid outputs on
the external SSD. No newly
staged source has entered training, and no source photos were modified.
