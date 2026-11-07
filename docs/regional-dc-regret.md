# V158: explicit pressure against regional color-bias increases

V158 tests a training-only RGB mean-error penalty on the unchanged V157 hybrid.
[V157](spatial-rgb-residual.md) reduced standalone coarse noisy-flat error, but
its quiet-neighbor total RMS rose 10–15% while spatial error fell slightly.
The independent pixel decomposition and native images identified larger regional
color bias. Fine real cab crossings also remained missing. The next comparison
must preserve weak response and quiet accuracy together, alongside the coarse gain.

Implementation and readiness checks pass; **restoration quality remains
unmeasured**. Both fixed 1,000-update heads are training, with the complete
four-endpoint review queued. The general inference recommendation is unchanged.

## Regional RGB bias regret

For output `O`, frozen V143 parent `B`, exact training target `T`, inherited
per-image noise unit `s` and native box width `w=32`, define:

```text
u = max(s / (w/2), 1/65535)
bB = box_mean(B - T) / u       # three camera-RGB channel means
bO = box_mean(O - T) / u
d  = box_mean(O - B) / u
q  = (1/65535) / u
rB = sqrt(mean_RGB(bB²) + q²)
rO = sqrt(mean_RGB(bO²) + q²)
regret = mean_RGB(d × (2 bB + d)) / (rO + rB)
```

The rationalized expression equals `rO−rB` without subtracting nearly equal
norms. Norm smoothing is 1 DN16; it does not quantize image pixels. The same
32px/hop16 replicated-boundary grid as the existing local loss covers every
pixel, including small and nondivisible rectangles.

The new loss averages a C1 positive hinge over boxes and images:

```text
h(r) = 0                    for r ≤ 0
       r² / (2 t)           for 0 < r < t
       r − t/2             for r ≥ t,   t = 1e−4
```

One fixed coefficient, **weight 1**, sits inside the existing domain multiplier.
Only the output receives its derivative; parent, target and units are detached.
The loss and first derivative are zero at unchanged parent output. Improving
an incorrect parent bias is unpenalized. No target or reference enters forward.

Dividing `s` by `w/2=16` uses the nominal square-root count of one Bayer phase
in an interior box. This deliberately gives mean error stronger training units
than pixel error. The 1-DN16 unit floor keeps small scales finite. This proxy
is **not calibrated post-demosaic covariance or boundary uncertainty**; repeated
edge samples and correlated restored RGB are not independent measurements.
Weight 1 is not equal-gradient-norm supervision.

The term sees channel means, so balanced zero-mean detail can remain invisible
to it. Existing RGB, gradient, delivered spectral and full-local-RMS terms all
remain active. A soft penalty can still allow worse regions, and the parent can
already contain false structure. Actual DC, spatial and weak-detail errors plus
native views remain required; this is not an inference gate or a safety guarantee.

## Fixed matched comparison

The [recipe](../configs/quality-v143-regional-dc-v158.yaml) fixes two identical
fresh `LateSpatialRgbDetail` heads, **117,677 parameters / 45 tensors each**:

| Arm | Loss difference |
| --- | --- |
| `dc-control` | Exact V157 spatial-hybrid recipe |
| `dc-regret` | Same recipe plus regional DC regret, weight 1 |

Architecture and all 87 neural source files remain byte-identical. Both heads
start fresh, with identical zero final outputs, on the same 1,000 V148 cached
batches / 4,000 old observations. The control must reproduce V157's complete
spatial-hybrid trace, raw/EMA/Adam states and all 1,644 actual reviewed outputs
exactly. No early checkpoint, coefficient, window or transition selection occurs.

Pixel/gradient terms, delivered-RGB spectral MSE coefficient .25, existing local
RGB-RMS regret weight 1, domain weights, physical conditions, geometry, shared
initialization, LR, AdamW, global clipping and EMA remain fixed. There are 882
supervised batches and 118 ADC batches with zero total gradient; all 1,000
optimizer/EMA clocks advance. Adding the term changes optimization pressure and
can invoke more clipping; its training value is not a quality result.

The supplied V143 parent already carries frozen official DINOv3 ConvNeXt-Small
guidance. Parent predictions, inputs and targets are reused without new
parent/DINO calls, noise draws, source lookups or RAW decodes. Protected GFX
captures, JPEGs and siblings remain excluded from training. Originals stay
read-only and `/mnt/dataz` stays unused.

## Readiness and actual live work

**56 CPU tests pass in 1.90s**: 11 new regional-DC cases plus 45 inherited
local/delivered/spatial tests. Independent NumPy code enumerates actual padded
pixel coordinates, channel means and full two-image output adjoints. Tests cover
small/nondivisible geometry, both hinge regions, finite identity derivatives,
detached inputs, tiny positive regret, the unit floor, free improving bias,
zero-mean detail and quiet regression despite better global error.

CUDA compatibility checks 28 archived native256/384/512/768 contexts across all
four CFAs and protected real controls, 56 actual head calls. Current and frozen
V157 spatial heads agree with archived outputs. Two discarded ten-update runs
include genuine save at update 8 and model/EMA/Adam/RNG restoration for the
remaining two steps. Production starts fresh.

An auxiliary CPU reporter initially used an obsolete prior-arm key and failed.
Its original source and error receipt are preserved. Revision 2 passes four
strict CPU model/EMA loads, all 90 finite Adam states at update 10 and exact
restored control raw/EMA/Adam against V157. All 90 parameter tensors receive
finite nonzero gradients over the prefix. The immutable 218-row production
snapshot matches every V157 control field exactly. The three controller/worker
owners were actually observed live by PID and creation time; the snapshot is
historical evidence, not a final count or endpoint. Training never restarted.

The [preparation publication](results/v158-regional-dc-preparation-v1.json)
preserves 12 byte-exact receipts, 33 source texts and all 87 unchanged neural
hashes, including the failed reporter and corrected revision. The
[verification](results/v158-regional-dc-preparation-verification-v1.json)
checks these bytes and document links. Mandatory final CPU validation of the
actual endpoint, all 90 Adam states, strict raw/EMA loads and exact control
trace/raw/EMA/Adam precedes review claims.

## Required quality review

Four fixed raw/EMA endpoints use all 822 cached cases: 3,288 actual review
calls, including 1,644 control archive replays before old array storage is
adopted. Two new prediction collections need **4.422 GiB entirely externally**.
Local storage is for metadata and publication only. New study reserves are
60 GiB local / 196 GiB external, plus .5 GiB projected margin. Old evidence,
policies and receipts remain unchanged; nothing is deleted or moved. RAM guards
remain 52 GiB at launch / 32 GiB at runtime, with a 12 GiB CUDA quota.

Each endpoint durably journals returned-forward events and complete observation
records. The queued postprocessors preflight the actual primary and independent
metric imports using their correct shared source directory. Expected scoring
remains 4,686 rows, with independent NumPy64/Decimal checks and 30 unscored real
rows. DC/spatial/full errors, mesh response, actual blank errors, natural detail
and ADC behavior remain separate. This reused related cohort is not blind validation.

The planned 72 native figures retain the 48 fixed boards and 24 repeated-cell
triplets: two meshes, two noisy flats and two quiet ROIs per endpoint. Every
board additionally shows the retained **V156 raw/EMA** quieter detail control,
with no new neural calls. The planned 39,705,600 RGB channels keep the same
160×160 original crop pixels, coordinates and transforms. Final manifests must
bind source/ROI, checkpoints, conditioning and exposure; actual viewing must
follow rendering. Repeated cells add no observations.

Both standing GFX scenes retain sky, building, foliage, coarse fence and both
fine-cab windows/priors, with both SOOC JPEGs. Independent ISO100/AHD/JPEG
references differ in aperture, shutter and motion: qualitative references,
**not exact GT**, never pixelwise scored. A successful next model must retain
weak real/natural detail while reducing quiet color bias, rather than merely
moving an average metric.

[Local-time diary](../diary/2026-11-07-01-34-28-v158-regional-dc.md).
