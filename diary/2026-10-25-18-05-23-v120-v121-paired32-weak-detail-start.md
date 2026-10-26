# Matched Small paired32 and weak-detail trials started

Recorded: 2026-10-25T18:05:23-07:00 (America/Los_Angeles).

The previous goal turn made concrete progress: commit161c033 completed and
published V119's quality/native review, recovered the missing RawNIND cases
without rerunning960 completed predictions, and extended the PSNR history.
The full PROMPT goal remains unmet; V119's known-camera and ADC-color regressions
motivate the next controlled quality work.

Started [V120/V121](../docs/paired32-weak-detail-training.md), both fresh20k
continuations from immutable V115 Small EMA fee5d05c... with the official frozen
Small backbone691963f0.... V120 retains V119's90791 Commons/six regions and
weighted camera probabilities, replacing corrected paired83 with corrected
original32. V121 uses the same paired32 and training settings but selects the
reviewed90787 corpus and fourteen-region weak photographic bank. The latter is
a combined four-source exclusion/ROI-bank intervention, not a source-count-only
ablation. Seed65, B16/native256/BF16, LR1e-5/warm200, domains, zero optical PSFs,
geometry-before-area2, epsilon.0003/paired.0001 and band0 remain fixed. The
prospective domain counts per arm are10013 Commons,5021 paired,4966 native.

Both discarded16-update CPU64/B1 and CUDA256/B16 checks pass for each arm:
64 actual implementation optimizer updates in total. All91 initial EMA tensors,
89 fresh AdamW states/steps, encoder identity/freeze, finite states, exact source
archives and all three domains verify. Twelve shared Commons/native inputs per
V120 check match retained V119 checks; five paired/native inputs per V121 check
match V120. Production restarts from the parent, with the first V120 loss exactly
matching its discarded CUDA check. V120 is live and has finite logged losses
through step600 at launch verification; V121 production is queued sequentially.
No intermediate checkpoint is read for evaluation.

Enabled source_loss_every100 in both. Actual diagnostic calls forbid neural
Module calls and check unchanged Python/NumPy/Torch CPU/CUDA random states.
They score existing outputs with detached FP32 singleton losses, not additive
training-loss contributions. The preserved launch prefix has32 diagnostic draws
at steps1/100, including procedural and photographic examples. Further visual
review can use actual current-model source IDs without rerunning the model or
changing either frozen training cohort.

Actual cached clean/paired/native readers pass before model execution; native128
source IDs form106 groups. No original RAW decode is needed. An initial
preparation check used rgb instead of camera_rgb and failed before any recipe,
plan or neural call; v2 corrects that plus the actual reader rows/native256
shape assertions. An initial launcher relative PYTHONPATH failed its import
before any controller claim/worker; corrected absolute paths launch the same
unexecuted controller. Both failed logs/sources/receipts remain preserved and
consume zero neural forwards/optimizer steps. No automatic retry is installed.

Queued eight FP32 endpoint stages for V120/V121 only (9172 root/encoder calls,
28380 primary/analytic observations), independent NumPy audit, and four saved-
output contrasts: V119→V120, V115→V120, V120→V121, V117→V121. Each contrast
includes full427 photo local detail,5124 cases and96075 reused GT blocks.
Native material/six GFX regions and both endpoints' four RGB16 exports receive
review/921600-channel quantization checks. All older control predictions are
reused. The additional3842/3835 green-mesh comparison under the two fixed profiles
and actual primary-agent viewing remain required before quality recommendations.
Each performance report will include at least two native noisy/restored/exact-GT
triplets; separately captured ISO100/AHD references remain labeled not GT.

[Launch evidence](../docs/results/v120-v121-training-start-v1.json) and
[verification](../docs/results/v120-v121-training-start-verification-v1.json)
check24 artifact bindings, all four discarded phases, exact recipe differences,
training/three queue guards and487 local Markdown targets. Exact identities of
the controller, V120 worker and all three waiting review owners are live.
48/24GiB RAM floors,24GiB CUDA quota,128/96GiB internal and208GiB external reserves
remain enforced. Runtime failures preserve actual work; no budget extension,
model promotion, new endpoint score, or overall goal completion is claimed.
Current docs and README now distinguish the active/queued trials from completed
V119 quality and the useful V114/V115/V117 choices.
