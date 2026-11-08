# Phase-aware readout completed quality and visible quiet-field costs

Recorded: 2026-11-08T05:06:01-08:00 (America/Los_Angeles).

V184 completes its original900-update readout training, raw/EMA quality review,
independent audits, reduction, rendering, actual native viewing, two strict
exports and actual browser checks. Train PID984348/create1794140356.75 and
review PID992275/create1794141129.42 are terminal. No successful training prefix,
review, audit, reduction or rendering is replayed. Preparation/native admission
and the training launch were committed/pushed03e28a24; this entry records the
completed quality result. The full fine-detail/clean-sky goal remains active.

The direct phase-aware readout is a useful stronger-response architectural path.
Versus its frozen V183 EMA initializer, mean constructed-mesh response rises
9.595924% raw/15.963283% EMA to4.864969%/5.147617% of exact GT amplitude.
Responses increase163/256 raw and160/256 EMA. Present full RMS falls0.650%/
0.938%, improving210/256 raw and194/256 EMA inputs. Raw has the smaller quiet
cost; EMA has the stronger mean response. Both primary comparisons use V183
EMA, including the new raw endpoint. Extra training,316 parameters and freezing
change together; this is not a matched total-budget loss-only comparison.

Quiet spatial RMS rises0.936%/0.765% raw and2.346%/1.807% EMA at ISO6400/12800,
worsening28/32 raw and29/32 EMA inputs. Quiet total RMS rises0.836%/0.575% raw
and1.855%/1.386% EMA, worsening28/32 raw and30/32 EMA. Quiet DC RMS improves
at ISO12800 while spatial error grows. Present blank RMS falls0.0341%/0.0178%
and absent full RMS0.0139%/0.0072%. Near-zero absent-template gains are reported
without relative percentages and are not a false-texture certificate.

Standalone512 full-flat RMS falls0.0094%/0.0086% raw and0.0060%/0.0037% EMA,
improving40/48 raw and37/48 EMA inputs. Coarse32 means rise by0.00012–0.00050%.
Natural fine-band response is mixed: raw increases60/128 inputs and EMA83/128;
all four relative band-error means worsen at each endpoint, with82/128 inputs
worsening. Neither tiny standalone-flat gains nor a larger band projection
proves broad photographic improvement or quiet-field safety.

Against V180 EMA, mean mesh response rises6.959% raw/13.174% EMA, though only
84/256 raw and93/256 EMA inputs increase. Against V181 EMA, mesh rises17.216%/
24.026%, with230/256 and229/256 increases; quiet spatial RMS remains higher.
Against V172 EMA, mesh rises25.477%/32.767%, but most responses decrease and
quiet error increases. EMA is1.760% below V161 EMA's mean mesh response while
quiet total RMS is10.703%/9.178% lower, improving31/32 inputs. Retain the direct
readout for further detail work, with raw's lower quiet cost, beside V183's
intermediate response, V181's quieter output, V172's balanced comparison and
earlier V173quiet/V171flat/V175rawquiet/V161detail strengths. V120 Small stays
the general recommendation. No study significance gate freezes that useful
architectural progress, and no mean establishes uniform detail recovery.

All60 actual figures/12 triplets were inspected in15 original-detail sheets.
At normal contrast mesh2302 remains nearly uniform; contrast40 shows clearly
stronger fine periodic modulation under persistent broad colored error, without
a complete lattice. Mesh2309 retains the strong orientation and loses the weak
crossing. Fine cab nominal/profile3879 windows show small strand-contrast changes
but remain soft/incomplete, without clearly complete new crossings beside the
independent references. Main coarse fence strands survive; building, foliage,
bird feathers, butterfly pattern and bark remain soft. The main sky looks smooth
at exposure4. Quiet steps/bars/stripes gain false regular fine structure, most
clearly with EMA at contrast40; some normal-contrast dark fields show faint
banding/diagonal modulation. Broad green/purple mottle persists. ADC bark/fur
and four planes retain exact inherited output. These observations keep the
original combined goal unfulfilled.

All189 inherited V183 EMA tensors remain frozen/eval. Only four new tensors/
316parameters train. The final204 weights/biases start at zero, with112 hidden
context parameters at a fixed local seed. All99 neural files remain sealed,
including the unchanged older98. Training uses the same1,000 cached rows,
900updates/3,600 noisy images/100ADC skips,nine V183 losses,clean mask and
domain weights. Head LR.001 has the same rowwise warmup/cosine schedule and
clipping1; head Adam/EMA starts at0, while inherited network/adapter retain
historical1800/900 clocks. Genuine row8 restoration resumes9 without replay.
Admission probes never initialize training. The independent audit checks all
900 exact FP32 totals, source/mask/LR/EMA bindings and five strict raw/EMA/
Adam/frozen/RNG checkpoints, with1,890 inherited-tensor comparisons. Final head
Adam is900; peak training CUDA allocation6,682,433,024bytes (about6.22GiB).

Quality completes1,644 wrapper/frozen,1,500 network/projection/readout and7,500
sampler calls. Every inherited V183 EMA and V169 output replays exactly:
1,644 bindings each, plus144 ADC identities. Independent audit checks6,576 input
fingerprints,72native RGB+72wave arrays,53,772,288 ordered baseline-plus-wave
addition channels,510 ordinary metric scalars plus72 wave-RMS scalars (582
total),278Decimal means and750 exact raw/EMA input-evidence pairs. The report's
582native-scalar and72wave-RMS counts overlap; the latter is included, as made
explicit by the scalar-count clarification receipt. No spectrum/confidence
calibration follows. The new output uses actual sequential FP32 arithmetic;
regrouping V169's older correction would change rounding. No model forward is
used by either independent audit.

Reduction retains21methods/17,262rows/38contrasts/1,386cells, with2,869Decimal
means and13,896paired checks. Both new primary contrasts use frozen V183 EMA;
36 contextual contrasts retain all19 older methods. A marked all-EMA fixture
has15,336paired checks because it shares older whole-correction RMS fields;
actual new wave-only RMS is a different quantity and is not compared with them.
The first comparison test run has12passes/two stale raw-role label failures;
source/log remain preserved. Correcting those labels and adding an explicit
both-primary-baselines-are-EMA check gives15passes. The first reducer/fixture
remain; v2 changes two human titles and seal filename only, with all numerical
bodies exact. No scientific calculation is repeated for that caption correction.

Full focused checks pass:36model/state,14training-audit,12quality-audit,
15comparison and16publication CPU checks. Actual live-owner/viewing guards reject
premature work before Torch/output creation. One review-preparation command
initially imported the working trainer rather than its sealed copy and stopped
before creating a review or importing Torch; loading the preparation entry with
the frozen import path fixes the launch plumbing. The original training and
review owners are never replaced or restarted.

Both strict193-tensor exports bind checkpoint SHA256
b99b2c72f0db0026cdbe9d8f1709e4fffd40b4412e1d9b5280874cb5b6e03576.
Raw exportfaf7efba78da5e6e3df13a48819c6659fb082cf3f42ae5b7e2de7fb4e1f6a51e;
EMA exportd454a04c7c3e090912592d0ff34036e54741c956f84b894363f2eba399c11d8b.
The actual viewer preserves all ten older method entries beside the new two,
defaulting V183 EMA/V184 EMA. All480 browser crops/36,864,000RGB channels match
source PNGs exactly;96 raw/EMA metadata pairs,click/F flipping,navigation and
absence of JS errors pass. The primary raw comparison also retains V183 EMA.
No fixture browser run or successful screenshot sequence is repeated.

The completed report retains both protected GFX families, main sky/building/
foliage/coarse fence and both fine cab ROIs/profiles/JPEGs, with12 native noisy/
restored/exact constructed-GT triplets. README embeds two new raw mesh triplets
and links older mesh/quiet strengths. All methods retain identical source/ROI,
physical noise, exposure,contrast,anchor and checkpoint metadata without pixel
resizing. ISO100/AHD/JPEG references are independent qualitative references,
not exact GT or pixelwise scoring targets; aperture/exposure/processing/moving
subjects differ. Protected captures,JPEGs,siblings stay excluded from training.
No new source/noise,parent/DINO,RAW decode,original or unavailable dataz access
occurs. The reused development suite supplies no blind or seed uncertainty.

Two publication resource checks stop at the local-space guard, before any
export or public output. Both logs remain preserved. A separate storage plan
fully hashes1,416 explicit original/public rendered-PNG pairs from21 completed
publications, checks69 recorded launch owners terminal and sees no active command
in those roots. Atomic hardlinks retain every original path/byte, with original
inode/mtime metadata recorded. Previous duplicate allocation345.203MiB is
recovered; local free space reaches48.708847GiB. An independent rehash of all
pairs and every current frozen training source precedes readmission. Observed
publication free space is48.708076GiB local/111.685520GiB external; source guards
and reserve constants stay unchanged. No scientific prefix is replayed.
V184 publishes35closed receipt paths and60PNGs through hardlinks to their private
artifacts, preserving bytes and avoiding redundant storage. Earlier native-array/
receipt and rendered-copy recoveries have distinct inventories and are not rerun.

The final verifier checks two strict exports and378 inherited tensors,1,386table
cells,60native figures/12triplets,8,294,400new and65,510,400copied display channels,
an additional36,864,000older-ten prediction channels recomputed from arrays,
480browser crops and current-document links. It binds this diary and the current
guides without altering earlier machine receipts. False quiet striping, missing
real crossings and broad colored mottle remain outstanding requirements.

[Completed quality](../docs/phase-wave-readout-comparison.md) ·
[Actual evidence](../docs/results/v184-wave-readout-final-v1.json) ·
[Native viewer](../docs/images/v184-wave-readout-v1/native-viewer.html) ·
[Browser verification](../docs/results/v184-wave-readout-native-viewer-verification-v1.json) ·
[Scalar-count clarification](../docs/results/v184-native-scalar-count-clarification-v1.json) ·
[Rendered-copy storage](../docs/results/v184-completed-render-copy-storage-v1.json) ·
[Publication storage readmission](../docs/results/v184-publication-storage-readmission-v1.json) ·
[Publication verification](../docs/results/v184-wave-readout-publication-verification-v1.json).
