# Fixed-background phase reconstruction

Recorded: 2026-11-16T19:10:15-08:00 (America/Los_Angeles).

# Protocol and implementation

Implemented fixed-global-background phase reconstruction. Preserve broad
Hann512/full-frame analytic frequency proposals and physical variance. Use the
global joint-fit nuisance coefficients, subtract a global competing H1 fit,
then apply a fixed local129/stride32/32-bin phase kernel. Held-out full/null
predictions and parent replacement use the identical composite A-only linear
operator. H1 controls keep their original scores.

The 48-case pilot adopts all88 previously closed fields with zero neural
replay. All corrections close before new quality scoring. It shares the
adaptive two-source development cohort; no generalization claim. Both
protected GFX families/profiles/ROIs/JPEGs are retained. Originals remain
read-only, captures/siblings stay outside training, independent ISO100/AHD
references are qualitative and never exact GT.

Frozen plan: `fbcee97a2c509d9512dd063c1416e0b83ed4cf4ac9c16852538e017a7d16b31b`.
Producer825313/create1794884732.1; predictor825336/create1794884740.18;
reviewer825314/create1794884732.12. CPU14/15, two threads, no restart.
The original full1164-case fixed-background sinusoidal run remains untouched
on CPU16/17, with its queued reviewer.

75 numerical tests passed initially;17 new operator tests passed again after
strengthening the H1 comparison to require actual nonzero corrections.
Ruff passes. A noiseless narrow-profile test verifies capacity only; actual
image quality and native viewing are pending. The new phase operator uses
a global competitor, while prior local129 sinusoidal WLS uses a local
competitor, so their comparison changes the full reconstruction rather than
isolating waveform capacity alone.

[Protocol/report](../docs/global-background-phase-reconstruction.md).

While the pilot runs, implemented the saved-baseline panel helper for the
separate full1164-case review. Its closed256 self-join reproduces all64 audited
native NN cells exactly and preserves every original board pixel. Actual full
current/prior rendering requires both completed collections and their audited
paired input match. Existing full launch receipts/snapshots remain unchanged;
[addendum evidence](../docs/results/fixed-bg129-full-setup-v1/baseline-panels-rehearsal-v1.json)
archives the helper and rehearsal exactly.

## Completed review

All48 corrections and all seven producer stages succeeded normally, followed
by the closed-cohort reviewer. Zero neural/DINO calls; all88 fields adopted.
Independent output audit:3819 fields/228 finite/114 material rows and14,131,200
encoded channels, maximum discrepancy2.95e-15. Actual inspection covered all38
published figures in11 exact unresized sheets, including both required native
triplets, both analytic triplets, paired sinusoidal/phase views, all protected
scenes/ROIs/profiles/JPEGs and all stress views.174 exact archives and165 frozen
source files are published with actual viewing receipts.

Neural400/far weak response rises4.695%→27.390%, strong51.780%→75.116%; both
sources gain weak response. Quiet/increment errors are+2.352%/+0.434% versus
parent. Source0 increment error worsens8.82672→9.00268 DN16; source1 improves
14.75054→14.67700. Full RGB RMS falls21.77841→21.41285, while weak-orthogonal
RMS rises11.38408→11.62419. Higher response/overall score alone does not prove
weak-detail fidelity. Analytic phase reaches28.558% and lower increment error
11.72513, but still worsens source0 and greatly increases real bands.

Actual viewing finds much stronger finite periodic modulation, almost no
high-noise weak recovery, unchanged sky, soft foliage/bark/fur and no convincing
new fine cab crossings. Neural building maximum rises15.55→75.18 DN16 at
[21,352,160,160]; analytic302.55→531.58 at[69,263,160,160]. Both exhibit real
color artifacts. Cab correction rises5.32/6.98 DN16 without convincing new
crossings. Preserve the implementation as a capacity/error tradeoff; no
preferred real-photo operating point or general V120 recommendation change.

95 relevant tests pass, including20 existing spatial regressions. The17 phase
tests were strengthened to require nonzero H1 parity; two actual full-context
standalone checks also match exactly. Ruff passes. CPU629.08s versus200.64s
for prior sinusoidal129, two threads; no100MP speed claim. README and current
research/index/report now document both the signal gain and error/artifact
costs. The original full1164-case comparison continues independently, with
no source mutation/restart or partial full-quality analysis.

[Complete evidence](../docs/results/neural-nuisance-phase129-v1/publication.json).
