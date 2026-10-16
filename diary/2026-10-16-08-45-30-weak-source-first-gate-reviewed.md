# Weak-source first gate reviewed without promotion

V55 finishes 1,000 updates on its original planned 4,000-step schedule; the
training/evaluation owner exits successfully. Same V43 EMA, fresh AdamW/EMA,
seed 52, batch 16, LR 3e-5, fixed reviewed paired83/native128/Commons40170 data
and original model/loss/noise/precision. Only weak_texture_fraction 0→.1 changes,
replacing half of the existing Commons procedural quota while preserving the
photo/flat probabilities. All 28 logged unchanged observations match V54;
all 13 replacement batches differ. Unlogged batches are not independently hashed.
Independent CUDA training is not claimed bitwise deterministic.

Candidate SHA 194e5b1ef23bdb893e0fbf6a3c05c29f4861c0e0735129bb1b9eb2a2d27254ea;
matched control is V54 step1000 SHA
975d47ffbd0cedc6ba2fa307d96265f1f3406d96bbeed6657bc32b44b37346d1.
Candidate minus control: known primary −.065092 dB [−.092084,−.038101],
unseen +.010899 [−.018183,+.039893], natural photo −.071013
[−.102323,−.044006], procedural −.422409 [−.702771,−.195621]. Source intervals
do not estimate training-seed uncertainty. All 86,828 synthetic-suite cases
recompute; 62,020 classical/RawNIND and 12,404 V54 neural cases replay exactly.

Actual GPU analytic evaluation completes all 1,344 method cases: 384 carriers
and 64 flats, two neural methods plus Malvar. At level .18, contrast .02,
high-noise prior, in-phase gain for periods 4/8/16 changes
.003324/.012822/.354528 → .002660/.024182/.324158. The 8px gain remains small;
response is mixed. Flat DC/RGB RMSE/spatial-band RMS are slightly lower, while
the .18 peak increases slightly. This is compatible with smoothing rather than
a clear texture-for-noise tradeoff, without proving the mechanism. Luma band
metrics can miss chromatic periodic errors; RGB RMSE is not a complete detector.

Visually inspected 36 native PNGs: V54/V55/channel-RawNIND across ten standard
subjects and all six neural analytic crops. Fine fabric remains lost, leaves
waxy and fence wires soft. Neural mesh geometry is more coherent than RawNIND,
but V55 adds no clear advantage. Weak carriers remain attenuated. Fixed 8-bit
flat previews show no obvious new structure, without excluding smaller errors.
All 46 native triplets verify SHA/geometry/metadata/shared noisy/reference bytes.
Eight full GFX RGB16 TIFFs verify complete SHA/bytes/dtype/16-bit tags/sampled
codes/ICC. GFX ISO100 remains a separate optical/time reference, never exact GT.

Decision: stop V55 at this first gate; no continuation or promotion. Preserve
the complete model/EMA/AdamW/Python/Torch/CUDA RNG state at step1000 and its
original schedule. The optional weak source remains default-off; V43 step2000
and README representatives stay fixed. This does not establish convergence or
reject weak augmentation generally. Report: docs/weak-texture-v55-review.md,
machine receipt docs/results/weak-texture-v55-review.json; publisher archived
under /mnt/external/demosaic/runs/publish-weak-texture-v55-review.py.

Earlier engineering checks remain valid: 472 frozen-source CUDA tests and
genuine-parent preflight, plus two metric tests and the separate CPU smoke.
This publication changes documentation/images only. The downloader remains
live at PID3989567, about 28.6k additional files/125.6 GiB this run at last check,
with 1.4 TiB free. Incoming data does not change frozen training membership.
Other users' GPU processes remain untouched. Broad quality/SOTA, protected-final
assessment and 100MP/10s remain open; the project goal stays active.
