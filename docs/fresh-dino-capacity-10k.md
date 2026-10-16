# Completing the original fresh-model schedules

The no-context, DINOv3 ViT-S and ViT-B arms continue from their complete 3,000-step
states to the originally planned 10,000 updates, sequentially on the shared GB10.
This finishes an existing controlled experiment; no optimizer, EMA, RNG or LR
reset is introduced. [Resume audit](results/fresh-dino-capacity-10k-resume-audit.json).
The [3,000-step review](fresh-dino-capacity-3k-review.md) remains historical evidence,
not convergence or proof of a general foundation-model effect.

All three retain frozen source `8580a4e`, seed 48, batch 16, LR 1e-4/original
cosine schedule, pinned genuine foundation weights, Gaussian CNN initialization,
physical anchors and BF16 training/FP32 physical operations. The explicit FP32
middle skip remains enabled in every arm so absent DINO does not change that
arithmetic. No query/value or input adapters are enabled.

Commons40170/native128/**original paired32** and all validation/test memberships
stay fixed. The opt-in83-ID corpus, weak fields and later inference flags are
separate experiments. Downloaded incoming data does not enter this continuation.
S/B differ in frozen features and corresponding projection width; they do not
isolate feature quality independently of adapter capacity.

The launcher requires the [V57 replay review](control-replay-v57-review.md) and
the preceding owner's actual exit. It checks source/config/manifest hashes,
original3,000 snapshot identities, complete AdamW at3,000 and matching stored/
installed PyTorch versions. The copied evaluation-only scripts have explicit
hashes. Main-worktree edits cannot change the frozen training package.

Each arm resumes model/EMA/AdamW/Python/Torch/CUDA RNG and performs 7,000 more
updates. Older1,000/3,000 snapshots stay intact. All403 logged observation hashes
must match across arms. Final quality review recomputes known/unseen development,
the full427-photo/16-procedural suite, analytic weak-carrier/flats and the complete
102 MP GFX scene. Native source/ROI/noise/display/checkpoint receipts and ten
RGB16 outputs are required. Protected-final scoring stays closed.

The [unchanged-control replay](control-replay-v57-review.md) shows why source
intervals cannot substitute for training-repeat uncertainty. This continuation
preserves the original compute policy and one training seed; it does not remove
that limitation. A finite completed schedule alone still does not establish
convergence, a DINO benefit, SOTA or the10-second speed target. V43 step2,000
remains the README reference until a complete review supports a change.

The [actual launch receipt](results/fresh-dino-capacity-10k-launch.json) records
controller164667 and the frozen source/plan identities. The no-context arm has
resumed at step3,001 with LR8.22411e-5 and finite updates beyond3,000; S/B follow
sequentially. All122 historical logged observations through3,000 remain matched.
Final10,000 quality/native results are pending.
