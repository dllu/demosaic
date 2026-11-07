# V159: wider quadratic pressure on small regional-bias increases

V159 changes only the regional-DC hinge transition on the unchanged V158
hybrid. [V158](regional-dc-regret.md) removed V157's large quiet color-bias
regression, but gave up nearly all of the coarse-flat gain and still weakened
mesh response versus V143/V156. Its 726/882 clipped supervised batches,
compared with V157's 67/882, motivate testing gentler gradients near the parent.
They do not establish that clipping caused the quality tradeoff.

**Implementation and readiness checks pass; quality remains unmeasured.**
Both fixed 1,000-update heads are training. Four final raw/EMA endpoints and
the complete independent/native review are queued. V158 quiet supervision,
V156 detail and V157 spatial/coarse strengths remain useful controls.

## One fixed transition change

The regional RGB mean-error regret `r` is exactly the
[V158 quantity](regional-dc-regret.md#regional-rgb-bias-regret): compare the
three-channel means of output/parent errors against exact training targets,
then take their smoothed vector-norm difference. Native32 boxes/hop16 use the
same replicated boundary grid, nominal units `u=max(s/16,1/65535)` and separate
1-DN16 norm smoothing. Parent, target and units are detached.

For one fixed transition `t`, the positive C1 hinge and its derivative are:

```text
h_t(r) = 0                 r <= 0
         r*r/(2*t)         0 < r < t
         r - t/2           r >= t

h_t'(r) = 0               r <= 0
          r/t             0 < r < t
          1               r >= t
```

| Arm | Regional-DC weight | Transition in regional mean-error units |
| --- | ---: | ---: |
| `sharp-control` | 1 | 1e−4, exact V158 recipe |
| `smooth-dc` | 1 | 1 |

At regret .1 the new derivative is .1, versus 1 for the sharp control.
At regret at least 1 both derivatives are 1; the absolute hinge values then
differ by a constant. A smaller training loss under the wider hinge is not a
quality result. This is one predeclared constant, with no coefficient/window/
transition sweep or early-checkpoint selection.

One regional mean-error unit is a training proxy. Its physical DN16 size varies
with image noise and has a 1-DN16 floor. It is not calibrated post-demosaic RGB
covariance, a fixed 1-DN16 allowance, confidence or a quiet-safety bound.
Improving parent bias remains unpenalized, and balanced zero-mean detail stays
under the existing RGB/gradient/spectral/full-local losses. A wider soft penalty
can permit larger regional regressions; actual errors and weak detail must be
measured together. No target or independent reference enters inference.

## Matched protocol and completed readiness

The [recipe](../configs/quality-v143-regional-dc-transition-v159.yaml) fixes two
identical fresh `LateSpatialRgbDetail` heads, 117,677 parameters / 45 tensors
each. All 87 neural source files and the loss implementation remain unchanged.
Only the per-arm transition differs. Base pixel/gradient terms, delivered-RGB
spectral MSE .25, local RGB-RMS regret 1, domain weights, initialization,
physical conditions, geometry, LR/AdamW/global clipping/EMA and all clocks are
fixed. Both use the same 1,000 cached V148 batches / 4,000 old observations:
882 supervised and 118 ADC batches with zero total gradient. All 1,000 optimizer
and EMA clocks advance. Production starts fresh after discarded smoke checks.

**60 CPU tests pass in 2.52s**: four new wider-transition cases and 56 inherited
checks. Independent NumPy code enumerates actual replicated/nondivisible box
coordinates, channel means and full pixel adjoints in both quadratic and
saturated regions. Perfect/imperfect parent identity cases verify detached
inputs, zero first derivative and finite second derivatives for the wider hinge.

CUDA compatibility checks 28 archived native256/384/512/768 contexts across all
four CFAs and real controls, 56 actual calls. Current/frozen V158 heads and
archived predictions match exactly. Two discarded ten-update runs include
genuine model/EMA/Adam/RNG save at update8 and restoration for the remaining two.
CPU checks load four states strictly, verify all90 finite Adam states and exact
sharp-control raw/EMA/Adam against V158. All90 parameter tensors receive finite
nonzero prefix gradients. An immutable **40-row production snapshot** matches
every V158 control field. All three original owners were actually observed live
by PID and creation time. This is historical prefix evidence, not completion.

The [preparation publication](results/v159-regional-dc-transition-preparation-v1.json)
preserves 11 byte-exact receipts, 33 source texts and all87 unchanged neural
hashes. The [verification](results/v159-regional-dc-transition-preparation-verification-v1.json)
checks those bytes, actual restored state/prefix and retained comparator bindings.
Final CPU validation must still establish all90 finite Adam states, four strict
loads and the complete1,000-row control trace/raw/EMA/Adam before review claims.

## Fixed full review

All four endpoints use all822 cached cases,3,288 actual head calls. The control
must replay all1,644 V158 outputs exactly before adopting old array storage.
Both new prediction collections,4.422GiB/1,644 arrays, write entirely externally.
Reserves remain60GiB local/196GiB external plus.5GiB projected margin;
RAM52GiB launch/32GiB runtime and CUDA12GiB. Old evidence is neither deleted nor
moved. Returned-forward and complete observation journals remain durable.

The queued actual primary/independent metric imports pass using the correct
shared source directory. Planned scoring is4,686 rows with NumPy64/Decimal
audits, all30 real rows unscored. Actual full/spatial/DC/quiet/coarse/blank errors,
mesh response, natural detail, ADC behavior and per-case costs remain separate.
Reused related CFA observations do not establish blind generalization.

The planned72 native figures include48 fixed method boards and24 triplets:
two meshes,two noisy native512 flats andtwo exact quiet crops per endpoint.
Every board also retains four **V156 detail / V157 coarse raw/EMA columns**,
without new neural calls. Planned47,078,400 RGB channels keep identical160×160
original crop pixels,coordinates and display transforms. Manifests must bind
source/ROI,checkpoint hash,noise conditioning and exposure. Actual viewing must
follow rendering; repeated cells add no observations.

Both standing GFX scenes keep sky/building,foliage/coarse fence and both fine cab
windows under nominal/profile priors,with both SOOC JPEGs. Independent ISO100
exposures/AHD/JPEGs differ in aperture,shutter,processing and moving subjects:
**qualitative references,not exact GT**, never pixelwise scored. Protected
captures,JPEGs and siblings stay excluded from training. Originals remain
read-only; cached observations require no source lookups,RAW decodes,new noise
or parent/DINO calls. `/mnt/dataz` remains unused.

[Local-time diary](../diary/2026-11-07-02-09-50-v159-dc-transition.md).
