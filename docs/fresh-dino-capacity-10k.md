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
updates. Older1,000/3,000 snapshots stay intact. All 403 logged observation hashes
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

The [first-arm boundary receipt](results/fresh-dino-capacity-no-context-10k-boundary.json)
now verifies that no-context finished all 10,000 updates: AdamW state is at
10,000, final LR is 1e-5, all 403 logged training losses/gradient norms and all
model tensors are finite, and the original source bundle remains unchanged.
The controller has moved to DINO-S, which resumes at 3,001 with the original
8.2241071e-5 LR and a matching observation. Its first 131 logged inputs through
3,200 match no-context; all 122 historical inputs still match across all three.
These are training-boundary checks, not final quality or convergence evidence.
S/B and the full numerical/native/analytic/GFX review remain. The controller will
make immutable 10,000-step model copies after all three arms finish; no expected
copy path was created early.

The [second-arm boundary receipt](results/fresh-dino-capacity-S10k-boundary.json)
now verifies that DINO-S also finished its original 10,000 updates with final
LR1e-5, finite recorded training/model values and a nonzero learned context
gate. All 403 logged observations match no-context. DINO-B has resumed from its
original 3,000-step state at the same 3,001 LR; the receipt records its matching
prefix through 3,150. These are historical boundary observations; B continues.

A [small matched no-context/S CPU review](fresh-none-S10k-cpu-review.md) reuses
the four fixed GFX contexts and two serialized exact-GT observations. It includes
ten native PNGs, four retained float predictions, and identical noisy/reference
pixels. Outputs remain close and fine detail still fails; no model is promoted.
The B/full-suite/analytic/full-frame review remains pending.

An [independent saved-score audit](fresh-dino-statistics-audit.md) is ready for
the completed results. It has actually rebuilt the historical 3,000-step panel:
100,528 case rows and 336 paired comparisons match the published arithmetic to
within 1.5e-14. The 10,000-step mode rejects the still-incomplete workflow before
writing a result; final 10,000 statistics have not been checked yet.

The saved fixed-eight-photo **training monitor** also needs attention in the
final review. Under the original CUDA BF16 EMA monitor policy, no-context's
PSNR changes 36.13900→35.18483 from 3,000 to 10,000, while SSIM changes
.962412→.964747. S changes 35.74417→35.38885 and .962205→.965376.
[Complete log snapshot and condition breakdown](results/fresh-original10k-monitor-snapshot.json).

| Monitor condition | No-context PSNR change, 3k→10k | S PSNR change, 3k→10k |
| --- | ---: | ---: |
| ADC-only | −0.5292 | −0.0606 |
| ISO100 prior | −2.0860 | −0.7896 |
| ISO1600 prior | −2.0913 | −1.2660 |
| ISO12800 prior | −1.4822 | −0.5134 |
| Legacy noise | −2.2666 | −1.7207 |
| Highlights | +1.3937 | +1.4179 |
| Shadows | +0.3824 | +0.4451 |

These are seven conditions/four CFA patterns on eight fixed monitor images,
not the pending full427/FP16 evaluation, real RAW primary scores or convergence
evidence. B's latest saved monitor in this snapshot is only 7,000 updates. Chroma
MAE also rises in the ISO100/ISO12800 monitor cases while gradient MAE falls;
that observation does not identify a cause. No
training policy or model selection changes here. Prioritize ordinary-noise,
highlight/shadow groups and native color/detail in the complete review before
choosing another experiment. The [CPU native examples](fresh-none-S10k-cpu-review.md)
use different precision/noise and are not images for these monitor scores.

The existing monitor-best states remain available for possible later review:
no-context 3k and S 1k match their already retained snapshots exactly in model
and EMA tensors. B's existing 4k best was copied from one opened checkpoint inode
to a private immutable diagnostic snapshot. This preserves evidence without
changing the trainer or creating the controller's expected final 10k paths.
The small monitor does not establish that these are broader quality optima.
