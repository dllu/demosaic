V184 adds a useful stronger-response architecture above frozen V183 EMA, with
new quiet-field artifacts. Mean constructed-mesh response rises **9.596% raw /
15.963% EMA versus V183 EMA**, reaching **4.86497% / 5.14762% of exact
constructed GT amplitude**. Responses increase on163/256 raw and160/256 EMA
inputs. Present-image full RMS falls0.650% / 0.938%, improving210/256 raw and
194/256 EMA inputs. The raw endpoint has the smaller quiet-field cost; EMA
provides the stronger mean response. Keep the direct phase-aware readout as a
detail-development option beside V183's intermediate response, V181's quieter
output and V180's earlier local architecture. V120 Small remains the general
photo/camera recommendation. The joint fine-fence/clean-sky goal remains open.

**Both primary comparisons use V183 EMA**, the actual frozen initializer.
These are additional head updates above a completed model, not same-total-budget
loss-only retraining. Extra training,316 new parameters and freezing change
together. The architecture supplies a separate learned wave path; it does not
isolate which of those changes causes the measured gains.

Quiet spatial RMS rises **0.936% / 0.765% raw and2.346% / 1.807% EMA** at
ISO6400/12800 versus V183 EMA. Spatial error worsens28/32 raw and29/32 EMA
inputs. Quiet total RMS rises **0.836% / 0.575% raw and1.855% / 1.386% EMA**,
worsening28/32 raw and30/32 EMA. Quiet DC RMS changes+0.200% / −0.108% raw
and+0.169% / −0.138% EMA; lower higher-noise DC error coexists with worse
spatial error. Stronger wave response is not a guarantee against false structure.

Present-mesh blank RMS falls **0.0341% raw / 0.0178% EMA**, improving223/256
and204/256 inputs. Blank spatial RMS falls0.0368% / 0.0194%. Absent full RMS
falls0.0139% / 0.0072%, improving217/256 raw and182/256 EMA inputs; absent
spatial RMS falls0.0151% / 0.0079%. Signed absent-template gains are near zero,
0.000001316 raw / 0.000004490 EMA. No relative percentage is assigned to that
near-zero quantity. These small blank-cohort improvements do not override
the measured and visible cost in quiet fields beside structure.

Standalone512 full-flat RMS falls **0.0094% / 0.0086% raw and0.0060% /
0.0037% EMA** versus V183 EMA. Full-flat means improve40/48 raw and37/48 EMA
inputs. Spatial RMS falls0.0100% / 0.0091% raw and0.0064% / 0.0040% EMA.
Coarse32 RMS rises0.00012% / 0.00050% raw and0.00012% / 0.00044% EMA.
Broad flat error remains; the tiny full-flat changes do not establish flat safety.

Natural photographic results are mixed. Across retained faint/dark and organic
faint/dark cohorts, raw fine-band response changes **+0.2018%, +0.0786%,
−0.0062% and+0.0153%** versus V183 EMA;60/128 inputs increase. EMA response
rises **0.3756%, 0.2147%, 0.0226% and0.0342%**, with83/128 inputs increasing.
Relative band-error means worsen in all four cohorts: **+0.0150%, +0.0158%,
+0.0010% and+0.0046% raw; +0.0267%, +0.0297%, +0.0013% and+0.0070% EMA**.
Eighty-two of128 inputs worsen in relative band error at each endpoint. A
larger band projection is not broad photographic fidelity improvement.

Against V180 EMA, mean mesh response rises **6.959% raw / 13.174% EMA**, but
only84/256 raw and93/256 EMA inputs increase. Quiet spatial RMS rises0.440% /
0.675% raw and1.843% / 1.716% EMA; quiet total rises0.405% / 0.584% raw and
1.419% / 1.394% EMA. Against V181 EMA, mesh response rises17.216% / 24.026%,
with230/256 raw and229/256 EMA increases, at1.15–3.03% higher quiet spatial
RMS. Against V172 EMA, mesh response rises25.477% / 32.767%, though only100/256
and103/256 inputs increase; quiet spatial RMS rises1.551% / 1.440% raw and
2.970% / 2.489% EMA. None of these means establishes uniform detail recovery.

EMA approaches the stronger learned V161 response: mean mesh amplitude is
1.760% lower, while quiet total RMS is10.703% / 9.178% lower, improving31/32
inputs. Raw has7.154% less mesh response than V161 EMA with11.596% / 9.904%
lower quiet total RMS, also improving31/32 inputs. This is a useful architectural
tradeoff. Keep V161's stronger response visible, together with V173's quiet
spatial reduction, V171's standalone-flat strength and V175 raw's modest
quiet-total gain.

All **60 actual native figures in15 original-detail sheets** were inspected,
including12 unresized noisy/restored/exact constructed-GT triplets. Mesh2302
remains nearly uniform at normal contrast. Contrast40 reveals clearly stronger
fine periodic modulation in V184 raw/EMA than V183, under persistent broad
colored error. A complete lattice still does not emerge. Mesh2309 keeps the
strong orientation, with the weaker crossing missing. Fine cab nominal and
profile3879 windows show small strand-contrast/modulation changes but remain
soft and incomplete; no clearly complete new crossings emerge beside the
independent ISO100/AHD/JPEG references. Main coarse fence strands survive.
Building edges, foliage, bird feathers, butterfly pattern and bark remain soft.

The main sky looks smooth at ordinary exposure4. Noisy gray/color flats retain
broad green/purple mottle at contrast40; ordinary gray/bright fields are nearly
smooth. Quiet ROIs beside vertical/slanted steps, narrow bars and stripe patches
show **extra regular fine striping/modulation**, especially V184 EMA, over the
broad colored field. Faint added banding or diagonal modulation can also be
seen in some normal-contrast dark fields. Boundaries survive, but these false
quiet structures directly qualify the response gain. ADC bark/fur and all four
ADC planes retain the exact inherited output. Zero-noise identities do not
establish noisy-sky safety.

Both protected GFX families remain in the report: DSCF3879 ISO6400 / independent
DSCF3880 ISO100 f/5.6 for sky, building, foliage and coarse fence; DSCF3842 ISO6400
/ independent DSCF3835 ISO100 f/5.6 and both camera JPEGs for the fine cab mesh.
**ISO100/AHD/JPEG references are qualitative, not exact GT**: aperture, exposure
time, processing and moving subjects differ. No real-reference pixelwise score
is used. Captures, JPEGs and siblings remain excluded from training. Originals
and unavailable `/mnt/dataz` remain untouched; only cached inputs and parents
are used, without new source/noise, parent/DINO inference or RAW decode.

Mesh triplets retain source cases mesh2302/mesh2309, native ROI
`[176,176,160,160]` in512px RGGB contexts, exposure8/contrast1, shot .00128 and
read variance6.5536e−6. Quiet triplets retain ROI `[80,176,160,160]`, exposure8/
contrast40 about camera RGB `[.001500000013,.006000000052,.002666666871]`, with
shot/read variance .00128/6.5536e−6 or .00256/2.62144e−5. Fine cab crops retain
context `[600,6260,768,768]`, ROIs `[206,229,160,160]` / `[426,189,160,160]`,
exposure16. All methods share identical coordinates and transforms; crop pixels
are never resized. Final training checkpoint SHA256 is
`b99b2c72f0db0026cdbe9d8f1709e4fffd40b4412e1d9b5280874cb5b6e03576`.
The two strict exports bind this checkpoint, source/class/config, raw/EMA state
and module hashes. All ten older viewer states retain separate metadata.

The model adds316 shared phase-aware readout parameters to frozen V183 EMA.
The same local RAW coefficients feed a6→16→12 pointwise contextual MLP, complex
mixing and explicit native subpixel phase transport. All189 inherited tensors
remain exact and in evaluation mode. The final204 readout weights/biases start
at zero;112 hidden parameters have a fixed local seed. New readout Adam/EMA
starts at0. One run adds900 updates/3,600 noisy images across1,000 cached rows
with100 ADC skips. All nine V183 losses, actual clean mask, domain weights and
cached data stay unchanged. Head LR.001 follows the same warmup/cosine schedule
and clipping1. The inherited network/adapter remain at1,800/900 historical
updates. Genuine row8 restoration resumes at9 without prefix replay. The
two admission probes never initialize this trial.

Independent training audit verifies all900 nine-term FP32 totals, input/mask/LR/
EMA bindings and five strict raw/EMA/Adam/frozen/RNG checkpoints, with1,890
inherited-tensor comparisons and final head Adam900. Training peak CUDA allocation
is6,682,433,024bytes, about6.22GiB. Independent quality audit verifies6,576 input
fingerprints,1,644 exact V183 EMA replays plus1,644 exact V169 replays,72 native
RGB and72 wave arrays,53,772,288 ordered addition channels,582 native metric
scalars,72 wave-RMS scalars,278Decimal means and750 exact input-only raw/EMA
evidence pairs. The new output is inherited V183 RGB plus the added wave;
regrouping the older V169 correction would change FP32 rounding. Local feature
geometry/powers are checked, without independent spectrum/confidence calibration.

All21 methods/17,262 metric rows, two frozen-V183 primary contrasts and36
contextual contrasts retain1,386 table cells,2,869 independent Decimal means and
13,896 paired checks. The marked all-EMA structural fixture has15,336 paired
checks because reused old correction-RMS fields are shared there; actual new
wave RMS is a different quantity and is not compared with whole older residual
RMS. Actual scientific losses, tolerances and core metrics are unchanged.
The first comparison tests caught two stale raw-role test labels;12 checks
passed and2 failed, with source/log preserved. Correcting only the labels and
adding a both-endpoints-use-V183-EMA check gives15 passes. The first reducer
source/fixture remain preserved; v2 changes two human-facing titles and seal
filename only, with all numerical bodies exact. No scientific work is repeated.

The reused development suite provides no blind or seed-uncertainty estimate.
The useful result is a stronger-response direct signal path with a raw/EMA
tradeoff, accompanied by visible extra quiet-field striping. Real missing
crossings and broad mottling keep the original goal unfulfilled.

The first publication command stopped at its local-space guard before creating
exports or public outputs; its failure log remains preserved. A separate
[completed-render storage receipt](results/v184-completed-render-copy-storage-v1.json)
records full-hash consolidation of1,416 explicit original/public PNG-copy pairs
from21 completed publications, with69 launch owners checked terminal. Every
path and PNG byte remains intact. Previous duplicate allocation is345.203MiB;
observed local free space then reaches48.708847GiB. No neural source, checkpoint,
training input, original or scientific result is altered, and no training,
review, audit, reduction or rendering is replayed. Public V184 receipt/PNG paths
share their closed private artifacts to avoid further duplicate storage.
