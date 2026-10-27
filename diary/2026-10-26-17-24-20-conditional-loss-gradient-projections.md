# Check mean-loss gradients against persistent fine detail

Recorded: 2026-10-26T17:24:20-07:00 (America/Los_Angeles).

The preceding turn made concrete progress: independent-noise mean-loss training
was implemented, four actual16+2 CPU/CUDA checks passed, and V124/V125 with all
endpoint/crop follow-ups were queued. Revalidated original V123 worker993796
and its controller4066396 as live, advancing through step2400 at this turn's
start. All original and new review owners were live. Worktree started clean.

Used the retained four-target/eight-noise-draw V120/V117 predictions to test the
new objective's mechanism without another neural call. For the pretrained RGB
branch, the auxiliary output is exactly mosaic(finalRGB), verified in the
actually evaluated frozen source and both checkpoint configurations. This makes
all five weighted reconstruction terms available from saved predictions.

Prepared a frozen CPU-only study:32 scene/model/CFA groups, each with8 original
outputs and28 unordered pair means. The other6 draws estimate target error
independently of a pair's gradient. Camera-RGB gradient/error projections use
the original target-selected16px DCT band1/8–1/3 and all eligible contrast bins;
reference-white display targets are derived only for loss replay. Original clean
references, outputs, input noise, corpus and active runs remain unchanged.

Completed1,152 functional output states,160 component-gradient calls and64 direct
control/mean-wrapper gradient checks. Neural Module calls were forbidden, CUDA
remained uninitialized and Torch RNG unchanged. NumPy closed-form camera/CFA
derivatives match within2.45e-7 relative error; direct planned-wrapper gradients
match reconstructed components within3.14e-7. The13 focused tests cover the
squared-error identity, signed finite-draw estimates, nonlinear held-out products,
component additivity and complete reconstruction-wrapper replay.

A separate NumPy-only verifier with explicit block extraction and cross-product
matrices reproduced all912 projection rows/16,416 scalar fields and228 CFA
averages; maximum absolute difference6.08e-18. All reference strata match the
original diagnostic. Saved gradients occupy about1.65GiB locally. No new
model/encoder forwards, input-noise observations, RAW decodes or optimizer steps.

V120's selected weak-fur/grass/wood bias-correcting projections rise2.79/3.11/
3.53%, while noise-covariance projections fall10.98/10.29/10.58%. V117 is similar.
Strong bark has a larger5.75% bias-projection increase, so this term is not a
selective weak-detail mechanism. All480 tested camera/display/edge/CFA local
projections are positive;120 highlight projections are zero. There is no
component-level opposition in these assessed directions. Model Jacobians,
heterogeneous batch masks, finite8-draw uncertainty and noisy native reference
estimates limit what this says about actual training.

Kept V124/V125's fixed settings. This modest output-space shift supports the
controlled trial, while actual grain/color/detail must be measured after full
training. Published the complete analysis, native scene-context triplets and
PNG/SVG plot. Actually viewed all8 plot axes; retained the first layout/source
with overlapping annotations and produced V2 with reserved annotation headroom.
No gradient or neural execution repeated for the layout change. Corrected the
fur image's human-facing license label to CC BY3.0, verified against its Commons
page; existing machine/source metadata already had the correct license.

[Current gradient report](../docs/conditional-loss-gradients.md) ·
[Complete projection data](../docs/results/conditional-loss-gradients-v1.json) ·
[Execution/publication/review receipt](../docs/results/conditional-loss-gradient-review-v1.json).

Updated related guides and removed stale current-V114/pending-V120 prose from
the visited V112/green-mesh pages. V120 remains recommended; V123 and the
V124/V125 chain continue under their original owners/plans. Full quality, SOTA,
broad real-camera superiority and100MP/10s remain unproven.
