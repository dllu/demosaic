# Input adaptation through genuine frozen DINO validated

Previous goal turn was progress: V55's full first-gate native/metric review
stopped the weak-data candidate without promotion. The project quality/SOTA,
protected-final and speed requirements remain open. Actual GPU process audit
finds no owned work after the prior owner's exit; foreign sriv jobs remain
untouched and the QI downloader remains live.

Current work adds an optional 6,531-parameter local RGB residual before DINO,
default false, zero final convolution, unchanged post-token adapter/gate and
physical reconstruction. Global CPU RNG is restored after module construction;
all common initial tensors remain exact. When enabled, autograd crosses the
frozen eval-mode encoder. No pretrained tensors are updated, no teacher or
feature loss is introduced, and the internal preview is not an image output.
This directly tests learnable input adaptation after fixed Wiener previews and
the current trained context branch failed to establish a clear general benefit.

Re-read primary Structural Guidance August 2026 and official DINO materials.
That paper adapts output tokens from fixed sparse pseudo-RGB; it does not prove
this new input policy. No copied upstream code or reproduced score is claimed.

Targeted tests pass (18 including shared adaptation tests). The complete
CUDA-enabled suite passes 483 in 47.39s. A small four-update CPU full/resume
fixture preserves learned input adapter/model/EMA/optimizer/RNG exactly. Genuine
V43 parent CUDA preflight initializes both full models identically on every
common tensor, with exact all-CFA FP32/BF16/FP16 initial outputs and native256
batch16 FP16 output. Two discarded BF16 updates per arm use identical batches.
Input-head gradients are nonzero at first update, earlier layers at second;
all original DINO weights remain exact. Nonzero learned portable reload is exact
FP16. Observed peak CUDA allocation 6.845/7.331 GB control/input, not a speed
claim. Receipt /mnt/external/demosaic/benchmarks/dino-input-v56-parent-gpu-v1/receipt.json.

V56 configuration changes only the new flag/run/notes against V54: same V43
EMA/fresh AdamW/EMA/seed52/B16/LR3e-5/planned4000 first1000, fixed83-ID paired
corpus/native128/Commons40170, original model precision/loss/noise and data.
Weak source remains off. A frozen-worktree controller will require all41 logged
training observation hashes to match immutable V54 first1000, then recompute
both networks and all baselines on known/unseen/full427/analytic-flat/fullGFX,
with native crop provenance and RGB16 validation. No quality promotion or
convergence claim follows from engineering validation alone.

Actual launch: frozen source 4bf85a2, controller PID59217 created1792166159.56,
log .cache/dino-input-v56-worktree/.cache/dino-input-training-workflow.log.
First input hash matches V54 exactly; independent CUDA first loss differs by
about2.5e-7, so exact optimization trajectories are not claimed. Six logged
observations through125 match. Source guards and full first-gate review run
inside the controller. Main source/preflight commit pushed successfully.

Independent CPU-only audit verifies original fresh no-context/S/B step3000
snapshots against their live last.pt copies, complete AdamW at3000 and all
Python/Torch/CUDA RNG, exact original source/configs and planned10000 schedules.
LR remains8.2252435921195e-5 in every arm. These schedules are unfinished,
not converged. A continuation driver is prepared without launching another GPU
job; V56 review takes priority. Audit receipt is public and original snapshots
remain untouched.
