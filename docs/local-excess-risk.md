# V156: local excess-error supervision beside weak detail

This active matched trial tests whether better strong-structure averages can
hide avoidable error in nearby quiet regions. [V154](robust-spectral-objective.md)
improved standalone flats but worsened mixed quiet patches; the
[matched parent comparison](matched-parent-comparison.md) did not remove that
tradeoff. **V156 restoration quality is not measured yet.**

The existing head already uses circular 3×3 frequency neighborhoods. This trial
changes local training pressure, keeping the head, data and inference identical.
There is no new inference mask or target-dependent forward path.

## Local RMS regret

For output `O`, supplied frozen parent `B`, exact training target `T` and the
existing per-image noise unit `s`, define `eB=(B−T)/s`, `eO=(O−T)/s` and
`d=(O−B)/s`. Each native 32×32 RGB box has:

```text
rB = sqrt(mean(eB²) + (1 / 65535 / s)²)
rO = sqrt(mean(eO²) + (1 / 65535 / s)²)
regret = mean(d × (2 eB + d)) / (rO + rB)
```

The last expression equals `rO−rB` without subtracting nearly equal squared
errors or RMS values. The one-DN16 term smooths the norm; it does not round the
image. Boxes overlap at native stride16. Replicated boundary samples and the
same half-hop grid cover every image, including nondivisible rectangles.

A C1 hinge with transition `t=1e−4` penalizes positive regret:

```text
h(r) = 0                   if r ≤ 0
       r² / (2 t)          if 0 < r < t
       r − t/2            if r ≥ t
```

The new term is the mean over boxes and images, with fixed weight1 inside the
unchanged domain multiplier. Improving boxes receive zero penalty. Parent,
target and noise units are detached in this term; only output receives its
derivative. Its value and first derivative are exactly zero at unchanged
parent output, including a perfect parent. Norm smoothing keeps derivatives
finite. The base pixel/gradient/spectral objective still drives initialization.

`s` remains the inherited whole-image RAW variance proxy with16-DN16 floor.
Noise units and the hinge transition are training scales, **not calibrated RGB
covariance, confidence or expected excess risk**. There is no clean-target-power
mask. The loss permits changes that reduce actual target error, including
denoising an already mottled parent.

Zero penalty does not prove pixelwise correctness, absence of false structure,
or safety on unseen captures. A box average can hide redistribution within the
box, the parent can already be wrong, and a finite soft penalty is no hard
constraint. Actual quiet spatial/DC errors, weak responses and native images
remain necessary.

## Fixed matched comparison

The [recipe](../configs/quality-v143-local-risk-v156.yaml) fixes two fresh
33,713-parameter/13-tensor relative-phase heads: unchanged RGB-MSE control and
the same objective plus local regret. All86 neural sources are byte-identical.
Delivered-RGB spectral MSE retains coefficient .25; pixel/gradient terms,
domain weights, physical conditioning, input evidence, frequency band/bound,
support, initialization, data/geometry, AdamW, clipping, LR and EMA stay fixed.
There is one local coefficient and two final raw/EMA endpoints per arm, with
no quality-driven coefficient or early-checkpoint selection.

Each head uses the same1,000 cached V148 batches /4,000 old observations:
882 supervised batches and118 zero-ADC-gradient batches. All1,000 optimizer/EMA
clocks advance, including momentum/decay coasting. The five training domains and
source geometry retain the V147 controlled recipe; no new noise, parent/DINO
call, source lookup, RAW decode or `/mnt/dataz` access occurs.

The MSE control must reproduce every V154 control loss/component/gradient/LR
row, raw/EMA/Adam states and all1,644 reviewed arrays exactly. Compatibility
checks precede two discarded ten-update CUDA runs with genuine8+2 restoration.
Production starts fresh. A mandatory strict CPU check of the actual final
checkpoint precedes the review claim and CUDA collection.

## Readiness and running work

Thirty-six tests pass in1.07s: nine local-loss tests and27 inherited delivered
objective tests. The independent local reference enumerates pixel coordinates
and repeated boundary samples, checking values and full two-image RGB adjoints.
Cases cover small/nondivisible images, saturated/quadratic hinges, exact zero
first/finite second derivatives, detached loss-only inputs, tiny positive regret
and a quiet-regression example despite better whole-image error.

Twenty-eight native256/384/512/768 compatibility contexts match frozen code and
archived outputs exactly:56 actual head calls. Both CUDA smoke checks pass;
all26 parameter tensors receive finite nonzero gradients over the prefix.
The preparation snapshot records active production with exact MSE-control trace replay at every completed
step. The immutable step500 CPU audit verifies26 finite Adam states and exact
control raw/EMA/Adam states. These establish engineering readiness, not quality.

The queued review fixes822 cases across four endpoints:3,288 actual head calls.
Both controls are evaluated and compared bitwise to their archives, adopting
those unchanged array files after replay. New local-risk raw outputs stay local,
EMA outputs external:2.211GiB each. This retains96/208GiB runtime reserves and
avoids duplicate control arrays or deletion of old evidence. Projected output
budgets include an additional0.5GiB margin per SSD. RAM guards are52GiB at launch
and32GiB runtime; CUDA allocation quota is12GiB.

Array scores retain4,686 rows, with30 real rows unscored, followed by a separate
NumPy64/Decimal audit. Seventy-two planned native figures use the same48 source
boards and24 repeated-cell triplets: two meshes, two noisy flats and two exact
quiet ROIs for each fixed endpoint. Every cell remains160×160 original pixels,
with identical ROI/transforms, checkpoint/source hashes, conditioning, exposure
and exact target anchors recorded. Actual viewing follows rendering; it has
not occurred yet.

Both standing real tests remain mandatory: DSCF3879/3880 sky/building/foliage/
coarse fence, and DSCF3842/3835 cab mesh under both priors/windows with both SOOC
JPEGs. Independent ISO100/AHD/JPEG references differ in aperture, exposure,
processing and motion: **qualitative references, not exact GT**. Captures,
JPEGs, siblings and validation sources stay excluded from training; original
media remains read-only.

The [preparation evidence](results/v156-local-risk-preparation-v1.json) preserves
the fixed plan, tests, actual compatibility/smoke receipts, step500 state audit,
frozen source texts and a timestamped live snapshot. Final training, actual
endpoint quality, independent final audits and native viewing remain pending.
The fine-detail/clean-sky goal stays active. See the
[local-time diary](../diary/2026-11-03-20-27-30-v156-local-excess-risk.md).
