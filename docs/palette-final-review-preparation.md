# Final palette review: serialized checks prepared

The original 4,000-update comparison is still training. A separately owned
controller waits for its **actual successful process exit** before any further
GPU work. It will independently audit both complete checkpoints and the main
photo/paired/analytic/GFX/three-camera reports, evaluate the same frozen hue
grid, and compare source-balanced scores with saved V43 and parent results.
Native visual review and the model decision remain separate pending work.

[Actual queue, frozen tools and verification receipts](results/palette-final-review-preparation.json).
[First1k quality review](wide-flat-palette-first1k-review.md).
[Original whole-state continuation](results/wide-flat-palette-full4k-launch.json).

The main audit now accepts the expected 1,000 or 4,000 boundary. It verifies
model91/EMA91/AdamW89 and RNG state, original source/data hashes, complete score
coverage and source intervals, shared controls, 70 native PNGs, 29 F32 contexts
and eight full RGB16 TIFFs. The final boundary has 162 logged observations,
including the resumed step 1,001. Logs are copied immutably. The first1k recheck
uses the preserved first1k logs while the live logs are being appended.

The hue evaluator reuses 2,352 verified parent/released-reference CUDA arrays
and infers 2,352 new arrays for the final control/wide pair. Exact observation
identities, model SHA/source, precision and memory format are required for
reuse. Every reused array is checksummed and independently rescored. This
avoids repeating unchanged networks and duplicating about 1.85 GB of F32
predictions. Three fixed preview cases across four methods produce twelve
triplets with native 160px panels.

The reuse path was actually exercised on all four first1k grid methods with
CUDA hidden and `--reuse-only`: **zero inference, zero new prediction files,
4,704 reused predictions**. All score rows, model metadata, 72 groups and
twelve entire PNG files match the preceding GPU report exactly. Independent
Torch64 checks of 28,224 metric fields agree to 4.45e-16, all native panels
rerender exactly, and 864 descriptive group values agree to 6.94e-18. The four
real precision policies are accepted; four altered policies are rejected.
The complete first1k audit still passes 87,962 rows / 252 intervals / all
artifacts, and all 48 saved-parent comparisons remain identical. Actual
premature final4k audit/evaluator invocations refuse to create outputs.

The queued eleven-script toolset and model package are frozen independently.
It leaves the running training, original manifests and standing GFX captures
untouched. The separate [physical preprocessing check](physical-frontend-color-check.md)
does not introduce a model change or imply that final quality has improved.
