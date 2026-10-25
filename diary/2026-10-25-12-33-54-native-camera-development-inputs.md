# Prepare native camera development targets while V119 trains

Recorded: 2026-10-25T12:33:54-07:00 (America/Los_Angeles).

While the original V119 Small run advances, prepared a supplementary native
camera development set. The existing128 native captures are all training-only;
they cannot supply independent test inputs. Inspected29 cached public RAWs
that were withheld for clipping, then39 native160 reference crops across12
photographic candidates. Eleven sources have suitable guarded256px regions;
the Nikon park source1416 has none and is dropped without relaxing the rule.
Selected20 regions before any model outputs, retaining source WB/matrix and
low-noise binned reference labels rather than exact noiseless-GT labels.

Completed a new finite identity screen against all103,604 current Commons
records, including older exclusions/reserves. Reused94,635 fingerprint entries
through a private SQLite backup and added9,212 verified missing cache entries.
The shared database is opened read-only. Seven source views/eight orientations
produce no dHash≤24/correlation≥.97 matches; all36 nearest-correlation source
suggestions were actually viewed and depict other subjects/compositions.

Verified native128 coverage as53 unchanged legacy sources/six prior public/
69 admitted public sources. Paired83 contains154 distinct clean references:
53 legacy,99 in the cached extension screens and two small Iain01 references.
One Iain01 view is already cached; only its second cached5.6MB NEF needs a new
identity render. The115-reference extra pool and inherited exact source screens
yield no matching candidate under the recorded finite criteria. All42 protected
screen hashes and current cached GFX3879/3880 source hashes verify. These are
capture/content checks, not proof that every geographic place/camera is unseen.

The original native4×/8× caches both trim one border. A12-ROI/four-CFA linear
ramp fixture verifies the one-cell4× offset exactly and catches the predicted
.0029296875 error when it is omitted. Each entire256 context plus a4× guard
stays below60000 in every cache channel; sensor-pixel clipping before averaging
is still a limitation. Twenty uint16 targets are copied without interpolation,
then their canonical FP32 camera values are shared by future methods.

The new data builder generates240 shared observations once: ADC/ISO100/ISO12800
priors ×four CFAs ×20 targets,16-bit ADC/black.03, CPU local generators keyed by
seed20261025/case/condition/CFA. All global Python/NumPy/Torch RNG states remain
unchanged; CUDA is uninitialized and neural Module calls are forbidden. Actual
training-loader use rejects the development manifest. Zero neural calls or
optimizer updates occur during all preparation; exactly one cached RAW decode
is needed for identity screening, and none for target/noise preparation.

Independent readback checks3,932,160 uint16 values exactly to source slices,
the same number of FP32 values and15,728,640 each noisy/variance values. The
independent variance formula agrees exactly; there is no noise regeneration.
Three unchanged native160 reference PNGs are published as source inspection,
without any model-performance claim.

The original V119 worker remains PID3134902/creation1792951461.96; the last
checked log is step5825, with finite losses/gradients/LRs and validations at
1000/2000/3000/4000/5000. All three original quality/audit/matched-review owners
are live and waiting as declared. Their frozen inputs/code remain unchanged.
New native-input prediction collection has not launched. Its future comparison
would be genuine new inputs, rather than replaying old comparisons for reporting.

[Native development set](../docs/native-camera-development.md) ·
[Selection and protocol](../configs/native-camera-development-v1.json) ·
[Preparation/readback/identity receipts](../docs/results/native-camera-development-inputs-v1.json).
