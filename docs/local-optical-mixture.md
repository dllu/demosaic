# Mixed pre-Bayer optics in regional weak-wire training

The [optical replay](sensor-optical-transfer.md) found that blur reduced
weak-wire recovery even after accounting for the detail removed by the
optics. This experiment tests whether exposure to a range of optical
widths during training improves recovery on an unseen width.

## Matched training

`local-optical-mixture-v1` continues from the Local 50k EMA as a fresh
1,024-update arm. It uses the [completed sharp-only regional arm](local-regional-wire-1024.md)
as the matched control. The model, regional and continuing-strand losses,
optimizer, learning-rate and EMA schedules, and source/order/camera seeds
match that control. Each arm observes the same 1,024 training sources and
six native observations per group. Half the groups use natural detail
and half use planted wires, with the established independent and
coupled sensor draws.

| Added Gaussian σ in native pixels | Source groups |
| ---: | ---: |
| 0 | 512 |
| 0.40 | 256 |
| 0.65 | 256 |

The optical widths are balanced within each source-kind, ISO, Bayer
pattern and noise-law stratum. The separable, unit-sum filter acts on
scene-linear RGB before exposure, camera conversion, Bayer sampling
and ADC. The target depicts the clean **post-optical** scene. It supplies
the detail available to the sensor, including its attenuated weak
wire. The mixed recipe retains 512 original sharp groups. These are
simulated optics widths.

## Frozen review

The primary test compares the new EMA with the sharp-only regional EMA
on the weak fundamental normalized by the original sharp target at
σ 0.85. The 24 new sources are disjoint from the training schedule, the
earlier wire panel and the fixed exact panels. Their appearances were also
checked against all 559,808 archived Corpus 100k photo visits. The 72
RAW fixtures were generated before the full training run began. A replay
on the earlier 32 sources checks consistency. Both panels include
σ 0 and 0.55, and the qualified synthetic captures share photon and
read noise across optical doses within each source and role.

The review also measures response relative to the available optical
target, continuing-strand and false weak projection inside actual
gaps, and luma RMS on exact flats. Fixed sharp natural-photo results,
both protected GFX comparisons, and the fixed 427-photo and two camera
panels are bound to their existing inputs. The review keeps the
original GFX camera references, exposures, coordinates and noise
profiles. The scope includes comparison against Local 50k, Corpus
100k and V120.

## Status

The eight-update GPU qualification is complete. The zero-blur input
audit reproduced 48 archived training and qualification fixtures
exactly. The mixed copies preserve camera and geometry metadata and
pixel-identical flat-core ground truth. The first full-run update
matches the sharp control's losses and gradient norm exactly. The
launch receipt verifies the first 60 full-run updates against the
frozen optical schedule. The [1,024-update endpoint](local-optical-mixture-1024.md)
now has a verified training receipt, both fixed exact panels, the 24
fresh optical sources and native reviews of both GFX scenes. The earlier
optical replay and matched-response diagnostic are running, with
the canonical panels queued.

At σ 0.85, the mixed EMA changes from a 0.247-point weak-response gain
over the sharp regional control at [128 updates](local-optical-mixture-128.md)
to a 0.361-point deficit at [512 updates](local-optical-mixture-512.md).
At the midpoint, false weak projection falls by 0.099 DN16 and flat
RMS rises by 1.069 DN16. The midpoint report also binds a finer-period
data variant that raises blurred wire coverage from 21 to 63 groups in
the evaluation period range.

[Launch receipt](results/local-optical-mixture-v1/launch.json) ·
[Frozen plan, sources and review scripts](results/local-optical-mixture-v1/launch-evidence.tar.xz) ·
[Main standing GFX review map](gfx-qualitative.md) ·
[Fine cab mesh review map](gfx-green-mesh.md).
