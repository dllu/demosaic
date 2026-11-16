# V131 broad numerical review

The [completed V131 continuation](v131-endpoint-quality.md) has useful targeted
faint-detail gains and a bark regression. Its broader photo/camera/texture/
color review is now being evaluated with the **original V120 primary
observation and metric pipeline**. Scores and independent audit are pending;
this is not a completed quality result.
[Frozen plan, compatibility, failed attempts and live-forward receipt](results/v131-broad-primary-v1/publication.json).

The frozen driver is [evaluate_v131_broad.py](../scripts/evaluate_v131_broad.py).
It evaluates the completed 20k EMA, SHA256
`4d78e6302f6e72d68acb03fe58eb7106763b8129ccb059747ef5d2cfbd3ec1e1`,
whose parent is V120
`a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb`.
All 91 restoration tensors and the frozen DINOv3 backbone are checked exactly.
The separate V132 run keeps its original 20k horizon and source.

| Panel | New V131 forwards | Numerical observations |
| --- | ---: | ---: |
| Photo + procedural | 3,108 | 12,404 |
| Known camera | 24 | 72 |
| Unseen camera | 30 | 90 |
| Texture | 112 | 448 |
| Color | 1,176 | 1,176 |
| Total | 4,450 | 14,190 |

The photo panel retains 427 free-image sources plus 16 procedural inputs,
seven conditions/four CFAs, native 256 FP32 batches. Existing V120/V121 controls
are reused without inference. Every new forward checks the original exact
argument fingerprints; photo targets and source/condition/CFA identities
also match their original witnesses. The old collector, data generation,
metrics and native prediction archive code are copied byte-for-byte.

The historical model parser does not recognize two newer configuration
fields. A narrow adapter removes only `raw_frequency_features=False` and
`raw_spatial_features=False`; any other or enabled extra field fails. It
changes no checkpoint or tensor. Both model implementations produced exact
matching outputs in a same-process diagnostic on two saved observations,
under both fixed/autotuned convolution policies and two repeats: 16 model/
encoder calls total, with all EMA and backbone tensors equal.

Three preliminary attempts are preserved. The first probe omitted explicit
noise conditioning and stopped. The second used contiguous weights against
saved `channels_last` output, with 0.13281 DN16 maximum difference. Matching
layout reduced the cross-session difference to 0.03906 DN16, still above the
initial arbitrary 0.01-DN16 limit. The current probe records actual differences
and uses explicit 0.25-DN16 maximum/0.025-DN16 RMS precision bounds. These are
numerical compatibility bounds, not image-quality gates; they do not relax
the exact checkpoint/EMA/backbone/input checks. Two compatibility forwards
precede the 4,450 panel forwards. Those three attempts did not reach a broad panel.

The fourth attempt passed both precision probes, then stopped at the old
checkpoint-cache write guard before any panel forward. The cache is now
inside the frozen work directory and all declared output paths are
preflighted. The fifth run has confirmed photo forwards; its archived progress
snapshot records 288/3,108 photo batches, not a completed score. Current probe
maximum/RMS differences are 0.039062/0.003808 and 0.027343/0.001616 DN16.
All four failed attempts, their sources and logs remain preserved.

All new outputs and checkpoint-cache writes are inside the project. Stage
entry requires 48 GiB available RAM; runtime retains 32 GiB, 128 GiB internal
disk and 96 GiB external disk reserves. The five numerical panels use prepared
inputs: no original RAW decode, training update or new independent noise
observation. Original corruptions are regenerated and fingerprint-checked.
Timing during concurrent V132 training is not a speed benchmark.

The [targeted native report](v131-endpoint-quality.md) retains the existing
same-checkpoint noisy/restored/GT triplets, faint gain and regression, and both
protected real GFX families with accurately labeled references. The broader
numerical result must be audited before reporting a new aggregate score.
