# Launch the matched camera-centering quality gate

Controller PID1150371 is live in `.cache/camera-centering-worktree` at7cd1f12.
Preflight passes: frozen module bytes match the genuine GPU preflight, recipe
hashes match, parent8ee3 verifies, run directories are new, and recipes differ
only in destination and matrix centering. V47 has begun actual training with
finite first loss/gradient, native-RAW input and6.95GB CUDA allocation.

[Launch receipt](../docs/results/camera-centering-v47-v48-launch.json) records
source/config/parent/driver hashes and the observed live workflow. Terminal/live
status is `/mnt/external/demosaic/runs/camera-centering-v47-v48-workflow.json`;
the executed driver is archived beside it. Private logs:
`.cache/camera-centering-v47-v48-workflow.log` and
`.cache/train-dino-camera-{control-b16-v47,centered-b16-v48}-1k.log`.
Do not modify this private source while running.

Sequential V47 thenV48,1000 updates each. The controller checks41 shared logged
batch hashes, complete AdamW step1000, frozen source archives and unchanged V48
reference in model/EMA. It then evaluates known/unseen, all427 photos plus16
procedural and full102MP GFX. Four RGB16 files get independent SHA/size/dtype/
shape/bitdepth/code/ICC checks. Publication still requires at least two native
exact-GT triplets per model and all four standing GFX crops, accurately labeled.

No other owned GPU benchmark/training overlaps. Commons downloads continue.
Current V43 step2000 and its immutable aliases remain fixed. The hypothesis
retains information and initial predictions; trained quality remains unproven.
The full SOTA/RawNIND qualitative, final-test, DINO attribution and10s goals
remain open.
