# Verify matched 40k training and quality-review handoff

Both original RAW-native arms have now completed40,000 updates:160,000 example
draws per arm, a quarter of the original640,000-example horizon. This is the
original full-state8k-to40k continuation, retaining source50dc11ec5c906fbbc4d3c5b1b530b95acb3b40a5f725d3a622891b2471c21d16,
B4/BF16, LR2e-4/warmup2k and the original160k-update cosine schedule. No new
diagnostic weights or data were admitted.

The exact training controller1745457/1792274479.6 and final DINO
trainer1932487/1792279710.17 have exited. The terminal training workflow binds
both checkpoints, finite model/EMA/Adam states, actual full-state restoration
receipts and metrics. All1602 logged observations per arm match in
step/domain/LR/batch hash, including the resumed8001 row; the first16 actual
observations additionally match the earlier frozen replay arrays.

No-DINO40k checkpoint SHA256:
`5708fdc19542ca1ef1aaafec25038dc049e4f5027782809846cf6d888ebed2cc`.
DINO40k checkpoint SHA256:
`4c2926e77dc5dea8580879eff9ebb69550fa891a295fa329a5800189c7fa8337`.
The genuine frozen DINO digest remains
`1d679a021c6c26b5a610281aff421afe8ec33ff0e18dc029c8da736eade9cc36`,
with no gradients or changed weights during training.

The existing review controller independently recomputes completed-boundary,
original8k ancestry, source/data/recipe/LR, model/EMA/Adam/RNG and complete
logged-input checks before starting inference. Its training-audit.json is
terminal-success and binds both actual40k states and the exited training owner.
GPU evaluation then starts successfully; the latest observed stage is full427
with exact child2099149/1792285394.04 confirmed live. Known/unseen stages have
exited before this next stage. No process was restarted or new GPU work added.

The fresh-coordinate CPU worker2012360/1792282156.8 automatically yields at
116 completed updates/arm while the owned review/timing sequence runs. Its
first128/256 evaluations remain pending; only64 has completed. The new real-GFX
conditioning worker already completed and exited before this handoff. Thus
neither owned CPU diagnostic adds compute during the quality/timing stages.

The public completed-boundary receipt is
`docs/results/packed-isotropic-quarter-training-boundary-v1.json`.
The production-learning note and requirements checklist now describe actual
completed training and a running review. This is provenance/handoff evidence,
without a40k quality gain, convergence, model promotion, protected-final score
or automatic continuation. Full metric/statistical/camera/hue/native review,
compiled execution and corrected-grid CUDA/full-frame validation remain.

The separate conditioning-sensitivity result and six native images were
committed/pushed in8654ba5. Nominal shot/read, active frozen protocols and README
representative model remain unchanged. SOTA, decisive real-photo superiority
and100MP within10s are still unmet/unproven.
