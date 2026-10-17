# Add optional RAW-head warmup with genuine-parent CPU checks

The preceding turn made progress: prepared, CPU-checked and queued the discarded
RAW-head CUDA fixture. Revalidated actual trainer 1988162 and downstream owner
identities. V64 continues to its 4k boundary under original 20k; its source/data and
every frozen review/CUDA operator remain unchanged. No owner was restarted or
new competing GPU work launched. Overall quality/speed goals remain incomplete.

Added the default-off training option `raw_kernel_only`. `make_optimizer` applies
the scope when constructing an optimizer, so portable reconstruction from a saved
config gets the same two parameter tensors. It freezes the full feature trunk,
RGB tail, measurement adapter and DINO projection/gates; the actual DINO backbone
stays frozen. Only AdaptiveRawKernel coefficient weight/bias train (22,032 scalar
parameters). Existing targets/losses supervise the head directly. There is no
teacher distillation, calibration, extra RGB output or altered reconstruction rule.

This makes an explicit head warmup possible before full joint optimization,
without backpropagating through the mature frozen feature network. It does not
claim that bilinear initial output retains V60 quality or that warmup improves a
trained model. Invalid non-boolean flags, incompatible refiner-only modes and
missing RAW-head configurations are rejected. Resume checks refuse changed
scope before any update; switching to joint training requires a deliberately new
run initialized from the warmup EMA, with a fresh optimizer/EMA and stated budget.

Six meaningful scope/optimizer/EMA tests were added. Targeted CPU suite: 37 passed.
Complete CPU suite: 534 passed/9 CUDA-related skips in 104.15s. No production source
change followed those checks. Current GPU fixture imports its archived 411d
candidate, not this changed root trainer.

Archived and executed an actual new-source CPU/B1/native64/FP32 fixture from V60
full4k EMA. Forced smooth Commons/workers0/val2, seed 48 and original 20k schedule;
first two Commons plus native/paired updates exercise all three domains. Four
updates versus 2+2 restart match all nine fields: model_config/model/EMA/AdamW,
Python/Torch/CUDA RNG, step and best. Numeric losses and input fingerprints are
exact. All 93 model/93 EMA/two AdamW finite, optimizer steps 4, only head weight/bias
change. Every one of 91 existing model and EMA tensors remains bitwise equal to
the mature parent. These discarded runs are not convergence or quality evidence.

Independently restored the actual two-state AdamW optimizer and trainable set.
All manual and portable EMA tensors, including actual DINO, and two natural-photo
FP32 predictions match exactly. An actual attempt to resume with full training
is refused before a checkpoint/update, preserving the warmup state. No CUDA
initializes. Both best values are 39.47513280596052; these fixture validation
values are not used for quality selection.

Also ran the new source with warmup disabled: all nine actual state fields,
numeric logs and input hashes match the genuine earlier completed 411d CPU
checkpoint exactly. New source bundle:
`32a330278824bb0b06b27a7b00439d10a3d853966ee3864ceb96a99ff08ae1c0`.
Operator/source/input/state/log/prediction receipts are under
`/mnt/external/demosaic/benchmarks/raw-kernel-warmup-CPU-preflight-v1/` and in the
new public result. The implementation adds no inference parameter or default
model behavior change. Actual GPU warmup memory/speed and trained quality remain
unverified; the queued original CUDA engineering fixture and current data model
review retain priority. Keep protected-final unscored and native/non-GT labels.


The matched training completed during this turn: both actual 4k checkpoints are
frozen, trainer 1988162 has actually exited, and primary 2036802 started evaluation.
V64 hash c0a00177b676caddea39b225f2fba1bcdc0b57d6fd543500363c8c908d83df81.
A read-only independent check of both actual boundaries passes original recipe,
state/EMA/AdamW/RNG/source/data and 161 domain/LR choices; all native/paired hashes
match, and 79 Commons/procedural-domain hashes differ. Both 20k schedules remain.
Public boundary receipt is separate from any quality result.

Completed early known/unseen panels have 810 cases. A CPU arithmetic/coverage,
metadata/control-witness check yields 42 comparisons and 14 witnesses. Expanded minus
control measured-CFA PSNR is -0.01989269dB on 4 known scenes, source-bootstrap 95%
interval[-0.03699038,-0.00279501], and -0.01278025dB on 5 unseen scenes,
interval[-0.02322334,-0.00247506]. Auxiliary unseen AHD RGB PSNR improves
0.03508551dB, while its SSIM interval includes zero. These are one-seed small
paired development panels, not training uncertainty, blind final or broad quality
conclusions. They show no measured-CFA gain from extra data at this boundary;
more data/longer training is not universally rejected.

Actually viewed all 8 paired native triplets and checked their exact saved V60
noisy/reference pixels and metadata. Both arms look similarly smooth on plates,
7D rectangles and warm apple/beige scenes, with no clear detail advantage. Real
low-noise/AHD references retain residual noise and are not exact full-RGB GT.
Also viewed 4 native photographic triplets from 2 exact synthetic targets. Both arms
erase the fine paraglider cords and soften cloud wisps/facade detail, with very
similar appearance. Noisy/GT pixels/ROI/noise/display transforms match across
arms. Receipts: long-commons-v63-v64-first4k-early-paired-review-v1.json and
long-commons-v63-v64-first4k-early-photo-native-review-v1.json under benchmarks.
These hashes can retain actual visual evidence for the later full review.
The 427-photo primary panel and later analytic/GFX/other-camera/hue/artifact work
remain running/pending. Keep V43/README and all existing model decisions intact.
