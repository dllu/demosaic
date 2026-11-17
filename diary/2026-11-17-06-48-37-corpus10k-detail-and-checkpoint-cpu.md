# Broader corpus midpoint loses weak detail; CPU checkpoint snapshots

Recorded: 2026-11-17T06:48:37-08:00 (America/Los_Angeles).

Previous goal turn: **progress**. It completed both scene-context primary camera
panels and their162-crop/648-row audit, viewed nine native camera boards, and
verified/published the actual7k checkpoint after the first storage repair.
It did not establish a weak-detail improvement or complete the photo panel.

This turn: **progress through new model evidence and a verified execution fix**.
The [control10k review](../docs/full-corpus-control10k-review.md) evaluates retained
EMA41d45a9c… against a fresh matched CPU V120. Actual coverage is53,506 distinct
photos/56,363 visits in160k target examples, already more sources than the older
20k V131/V132 continuation. All40 conditioning chunks and10k global indices
are checked. Native/paired source IDs were not recorded; their catalogue counts
are not invented as actual distinct visits.

The wider coverage has not yet improved weak detail: faint ADC−0.61431 dB,
all four materials regress, and98.89% of added camera-RGB MSE is spatial.
Ordinary/shadow means improve only0.00118/0.00362 dB. The selected eight ADC
flat inputs have lower maximum mean bias but higher centered RMS. The existing
fixed ADC projection makes all valid observed samples exact, yet missing-color
MSE remains higher; its partial PSNR repair does not remove the regression.
No causal attribution to source count, quota or precision is made because those
recipe/execution changes co-vary.

110 retained observations produced220 CPU restoration calls,110 actual local
DINO executions and110 verified replays in590.453s excluding load. No new neural
GPU/RAW/noise/optimizer calls were needed for the review. All26 raw and6 physical
diagnostic native boards were actually opened;22 triplets are exact subsets.
Both [main GFX](../docs/gfx-qualitative.md) and
[cab-mesh](../docs/gfx-green-mesh.md) comparisons remain soft/incomplete, without
convincing new fine crossings. The independent audit checks256 metric rows,
120 original-source strata,32 boards and22 triplets. Corrected audit path/name
errors and the initial missing-source-ID assertion are retained as failures.

The live control then suffered a second actual serialization stall at14k,
now in first `last.tmp`, after complete13k. Thus the first best-link fix was
insufficient. [CPU checkpoint recovery](../docs/full-corpus-checkpoint-cpu-recovery.md)
retains13k3810d5ba… and all partial/source/log evidence. Only the exact owned
worker was SIGTERM'd, and its controller exited−15. No other process was stopped.
New frozen v7 changes only checkpoint storage/logging and redundant final save;
raw/EMA/Adam/RNG/data/noise/precision/20k and100k horizons are unchanged.
All37 regression tests pass. Actual13k CUDA state was CPU-snapshotted,
serialized/reloaded twice with every nested value exact, without neural calls.

The remaining7k control updates resumed, followed automatically by the remaining
99k long-arm allocation. The lost13001–14000 segment is replayed, not counted
twice. First250 actual source rows and all250×16×14 conditioning values match
the abandoned segment exactly; published optimizer progress passes13,500.
The next full checkpoint is separately observed, not inferred from liveness:
actual14k8259e05a… saved in0.5304s with all91 raw/91 EMA/89 Adam states finite,
all Adam steps14k and RNG/CPU tensor ownership verified. Training then passed
14,125. The [production addendum](../docs/results/full-corpus-checkpoint-cpu-recovery-v1/step14000-addendum.json)
preserves that later observation without altering the initial publication.
The scene full427 CPU collector is also still active under its original owner.

Training completion, scoped numerical completion and native viewing remain
separate. V120 stays recommended. The [PSNR chart](../docs/performance-history.md)
remains through V131's last complete three-panel evaluation: no midpoint or
four-source score is promoted to a full427 point. README remains77 lines;
current-model, experiments, research, index and both GFX maps link the new
negative result. Original receipts/sources are published byte-for-byte; large
weights, predictions and private RAW remain local. Complete20k/100k horizons,
learning curves and broad endpoint panels remain pending.
