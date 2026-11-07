# V170 released learned RAW matching comparison

The released NLFeMF checkpoint does not improve our fine-wire goal in this
pipeline. Direct Malvar and the DINO-parent hybrid recover respectively
2.533% and 2.406% of constructed mesh amplitude, versus V169 EMA's3.837%.
Present-mesh RMS rises6.96–7.56%; absent-field RMS rises8.02–8.85%. The nominal
cab prior erases much of the green fence, and the alternative prior gives
speckled, incomplete strands. Neither reconstructs the crossing family.
The main coarse fence is also rougher and less continuous. Sky appears smooth
at ordinary display, while building and foliage show no decisive new gain.

There are useful but limited quiet-field results. Compared with V169 EMA,
quiet spatial RMS falls6.26–7.74% at ISO6400 and29.27–32.71% at ISO12800.
Total quiet RMS instead rises2.15–4.09% and9.28–11.66%; DC color error rises
24.30–27.58% and101.07–103.01%. Native crops show purple/red casts and residual
blobs. Native512 coarse-flat means fall15.79–15.87% and19.22–19.38%, improving
16/24 and22/24 inputs for either return. ISO12800 total-flat RMS falls1.71–3.30%,
while ISO6400 total-flat RMS rises17.67–19.03%. A smoother field alone is not
sufficient for fidelity.

Faint/dark natural textures weaken: retained-photo band response falls28–37%,
with higher RMS in all128 method/input comparisons in that cohort. Low-noise
ADC-only photo and plane controls show a fine periodic colored pattern in both
returns, absent from the constructed GT. All72 ADC control inputs worsen in
full RMS for both returns. Direct Malvar also adds visible edge fringes;
keeping the DINO interpolation residual reduces some fringes, with higher total
quiet/mesh error. These are results for this external checkpoint, our supplied
noise maps and two RGB reconstructions; they do not establish an architectural
limit for learned matching or an equivalence to training on our free images.

All60 fixed native figures were actually viewed in15 original-detail sheets.
Keep the pinned port, sampler checks and measured coarse/spatial tradeoff as
research evidence. Retain V120 Small as the general recommendation and the
V169/V161/V165 and earlier strengths alongside their documented costs. Fine
crossings without fabricated flat-field structure remain unresolved. A future
matching experiment would need matched free-image training and explicit
low-noise/constant controls before treating these weights as a starting point.

[Final evidence and exact sources](results/v170-nonlocal-raw-final-v1.json) · [Native pixel,checkpoint,noise and display metadata](images/v170-nonlocal-raw-v1/manifest-v1.json).

## Mesh and actual blank error

| Metric | V143 parent | V168 EMA | V169 EMA | NLRaw Malvar | NLRaw DINO hybrid |
| --- | ---: | ---: | ---: | ---: | ---: |
| Present full RMS | 9.111243 | 8.943902 | 8.956287 | 9.579194 | 9.633410 |
| Present signed template gain | 0.02202090 | 0.03835930 | 0.03836594 | 0.02532680 | 0.02406318 |
| Present actual blank RMS | 5.523323 | 5.589461 | 5.609300 | 6.006347 | 6.054005 |
| Present blank spatial RMS | 5.343113 | 5.407807 | 5.431940 | 5.825869 | 5.873875 |
| Present blank DC RMS | 1.289621 | 1.300783 | 1.289568 | 1.345928 | 1.350164 |
| Absent full RMS | 5.237910 | 5.290214 | 5.305929 | 5.731646 | 5.775445 |
| Absent signed template gain | 0.00003236 | -0.00000810 | -0.00000719 | 0.00085482 | 0.00078522 |
| Absent actual blank RMS | 5.237910 | 5.290214 | 5.305929 | 5.731646 | 5.775445 |
| Absent blank spatial RMS | 5.099652 | 5.146561 | 5.169538 | 5.589938 | 5.632968 |
| Absent blank DC RMS | 1.098115 | 1.128089 | 1.098120 | 1.157654 | 1.165142 |

## Quiet fields beside edges

| Metric | V143 parent | V168 EMA | V169 EMA | NLRaw Malvar | NLRaw DINO hybrid |
| --- | ---: | ---: | ---: | ---: | ---: |
| iso6400-prior whole RMS | 27.105631 | 26.831196 | 26.806949 | 67.263820 | 53.082994 |
| iso6400-prior quiet RMS | 3.898845 | 4.203388 | 4.046127 | 4.133232 | 4.211560 |
| iso6400-prior quiet spatial RMS | 3.268502 | 3.433879 | 3.439626 | 3.173338 | 3.224389 |
| iso6400-prior quiet DC RMS | 2.016074 | 2.279202 | 2.018205 | 2.508630 | 2.574805 |
| iso12800-prior whole RMS | 36.747466 | 35.550733 | 35.462223 | 76.100543 | 65.269226 |
| iso12800-prior quiet RMS | 6.152652 | 6.745842 | 6.344343 | 6.933188 | 7.084074 |
| iso12800-prior quiet spatial RMS | 5.341833 | 5.547922 | 5.559786 | 3.741196 | 3.932723 |
| iso12800-prior quiet DC RMS | 2.849060 | 3.617679 | 2.853327 | 5.737168 | 5.792642 |

## Native512 standalone flats

| Metric | V143 parent | V168 EMA | V169 EMA | NLRaw Malvar | NLRaw DINO hybrid |
| --- | ---: | ---: | ---: | ---: | ---: |
| iso6400-prior full RMS | 18.546808 | 18.546646 | 18.618871 | 21.908543 | 22.161317 |
| iso6400-prior spatial RMS | 18.235130 | 18.237235 | 18.308796 | 21.231103 | 21.495424 |
| iso6400-prior coarse32 RMS | 13.440561 | 13.367796 | 13.438463 | 11.306463 | 11.316815 |
| iso12800-prior full RMS | 24.071890 | 24.086164 | 24.219097 | 23.420437 | 23.805270 |
| iso12800-prior spatial RMS | 23.596861 | 23.649192 | 23.747288 | 22.797474 | 23.199656 |
| iso12800-prior coarse32 RMS | 17.932544 | 17.832479 | 17.930574 | 14.455324 | 14.484090 |

## Natural photographic detail

| Metric | V143 parent | V168 EMA | V169 EMA | NLRaw Malvar | NLRaw DINO hybrid |
| --- | ---: | ---: | ---: | ---: | ---: |
| retained512/photo-faint full RMS | 33.963754 | 33.968609 | 33.966492 | 36.550332 | 36.667950 |
| retained512/photo-faint band response | 0.298560 | 0.297996 | 0.298025 | 0.200910 | 0.188582 |
| retained512/photo-faint band error | 0.824639 | 0.824695 | 0.824693 | 0.881744 | 0.886423 |
| retained512/photo-dark full RMS | 29.097715 | 29.098256 | 29.094009 | 32.565825 | 32.654174 |
| retained512/photo-dark band response | 0.531446 | 0.530871 | 0.530900 | 0.380704 | 0.358915 |
| retained512/photo-dark band error | 0.661447 | 0.661254 | 0.661251 | 0.749796 | 0.757022 |
| organic384/photo-faint full RMS | 37.469061 | 37.487138 | 37.483612 | 38.473388 | 38.566351 |
| organic384/photo-faint band response | 0.150701 | 0.149124 | 0.149160 | 0.107300 | 0.099109 |
| organic384/photo-faint band error | 0.924117 | 0.925055 | 0.925058 | 0.943777 | 0.948268 |
| organic384/photo-dark full RMS | 33.685796 | 33.690339 | 33.685928 | 35.096149 | 35.239609 |
| organic384/photo-dark band response | 0.398945 | 0.397768 | 0.397799 | 0.293132 | 0.271221 |
| organic384/photo-dark band error | 0.781612 | 0.781689 | 0.781691 | 0.821577 | 0.830531 |

## ADC-only controls

| Metric | V143 parent | V168 EMA | V169 EMA | NLRaw Malvar | NLRaw DINO hybrid |
| --- | ---: | ---: | ---: | ---: | ---: |
| Photo full RMS | 18.149871 | 18.142182 | 18.142182 | 44.472108 | 39.478033 |
| Photo band error | 0.101855 | 0.101800 | 0.101800 | 0.367385 | 0.351139 |
| fresh-flat512 full RMS | 3.322910 | 3.322910 | 3.322910 | 25.265195 | 25.472060 |
| fresh-flat512 coarse32 RMS | 0.538587 | 0.538587 | 0.538587 | 3.001367 | 2.976424 |
| adc-sloped512 full RMS | 3.771369 | 3.776943 | 3.776943 | 31.519579 | 31.790693 |
| adc-sloped512 coarse32 RMS | 0.574652 | 0.573442 | 0.573442 | 3.037036 | 2.999375 |

All RMS values are camera-RGB DN16. Signed template gain1 means the constructed mesh amplitude;a small signed absent mean does not establish absence of artifacts. Coarse32 is spatially centered block-mean error. Means/counts and every paired difference are retained,without significance or blind-generalization claims.

## External checkpoint and implementation

The [April2026 NLFeMF paper](https://arxiv.org/abs/2604.17453) describes learned matching and filtering on noise-conditioned RAW. This comparison uses the [official v1.0.0 release](https://github.com/MIA-UIB/nonlocal-matchfilter/releases/tag/v1.0.0),commit `6df6a79ce128a7741af88ff0f3e9794f9b5e03d4`. Its external RAW training data differ from our freely licensed image pipeline. This is a pipeline comparison,not an isolated architecture or training test;training media were not downloaded,and no blind split equivalence or training-image license equivalence is claimed.

The selected seven original class definitions match upstream ASTs exactly. All141 tensors/15,282,866 parameters load strictly. The pinned deform-neighbourhood v0.1.1 CPU/CUDA sampler is built for GB10 without changing its interpolation. Four independent NumPy sampler fixtures match CPU/CUDA. Original and copied full networks are bit-identical on CPU;CUDA parity differs by at most2.24e-8 normalized. This admission used two CPU and one CUDA full-model calls,separate from quality. All13 independent Bayer/conditioning/consistency CPU tests pass. MIT notices and embedded Caffe notices remain in the source evidence.

The frontend flips native Bayer geometry to RGGB and uses RGBG channel order. It supplies noisy RAW clipped0..1 plus the square root of the inherited noisy-input variance. Output RAW clips0..1 as in upstream evaluation. Targets and references never enter inference. One neural call provides two fixed outputs:`Malvar(denoised RAW)`;and `V143 parent + Malvar(denoised RAW - CFA(parent))`. The second retains the DINO parent's interpolation residual while changing measured sensor samples to the RAW estimate,up to FP32 rounding. Signed residuals/final RGB are not clipped. Neither return is a calibrated detail detector.

Original checkpoint SHA256 `b31bc8e21022389b0b209a9d1e6649485ed4dacc552b7ea04612df5f7515fcf2`;tensor-only checkpoint SHA256 `a891235b053ef00072d411d53feba65120ffe903f15bee32b5017fd39e700b51`. The restricted extraction substitutes inert classes for unused OmegaConf metadata rather than executing checkpoint code. All91 previous neural source files remain unchanged.

## Work and audit scope

All822 cached cases completed once:822 actual quality neural roots,with4110 nested learned-sampling calls. Outer wrapper and nested network counts describe the same822 calls. The two RGB returns give1644 streamed metric rows. Admission adds one discarded synthetic CUDA full-model call and two CPU calls;total new CUDA full-model calls are823. No new source/noise,training,parent/DINO or original/dataz reads occurred. Both recorded worker owners are terminal.

All822 event/input/parent bindings,3288 actual input fingerprints and1644 durable RGB rows are audited. Full arrays are retained only for36 preselected native cases:72 RGB plus36 RAW arrays,250,951,168 bytes. Independent saved-array metrics check 570 scalar values. NumPy64 independently reconstructs 53,772,288 RGB channels from those RAW outputs and parents;maximum discrepancy is 0.012779 DN16. Other new outputs were scored/fingerprinted and RMS-norm/decomposition checked in process;there is no complete new full-array archive or all822 new-array posthoc audit. Independent Decimal means check 613 reductions.

Peak quality CUDA allocation is2.420598GiB. Recorded wrapper-forward intervals total210.214s,median.278519s across mixed128–768 native contexts,including two Malvar returns and excluding disk/metric work. These intervals are not a matched whole-pipeline/full-frame speed benchmark;the hybrid also depends on a cached DINO parent. No100MP inference or10-second claim is made.

A new bounded-trial policy reserved52GiB local/114GiB external plus.5GiB projection margin,32GiB runtime RAM and12GiB CUDA;old studies' guards remain unchanged. Shape-metadata preparation failure and a missing-helper initialization failure are preserved with exact source/log evidence. Both preceded held-out inference. The verified helper was added through a separate prelaunch receipt,without changing the frozen inference AST/plan. No completed scientific forward repeated. [Original protocol](results/v170-nonlocal-raw-v1/original-protocol-v1.md) · [Preparation](results/v170-nonlocal-raw-preparation-v1.json) · [Dependency correction](results/v170-runtime-dependency-preparation-v1.json).

## Fixed native comparisons

Every cell is160×160 native pixels without resizing. The48 boards and12 noisy/restored/exact constructed GT triplets preserve V169 coordinates,noise,transform,exposure,anchor and contrast. All60 figures were actually viewed in15 original-detail sheets. Source/ROI,CFA,noise conditioning,checkpoint hash and display exposure are bound in the manifest. The synthetic mesh uses RGGB512,ROI `[176,176,160,160]`,shot.00128/read variance6.5536e-6,exposure8,contrast1/40. Quiet fields useROI `[80,176,160,160]`,exposure8,contrast40;native flats useROI `[176,176,160,160]`,exposure4,contrast40. ISO12800 uses shot.00256/read variance2.62144e-5. Per-case anchors and camera transforms are in the manifest. Photographic credits/licenses remain in the [V168 source report](fine-mesh-training.md#photographic-credits).

The standing main DSCF3879 ISO6400/DSCF3880 ISO100 scene includes sky,building,foliage and chain-link fence at exposure4. Cab DSCF3842/DSCF3835 includes both noise priors,two160px windows `[206,229,160,160]`/`[426,189,160,160]` in768px contexts,exposure16,and both camera JPEGs. ISO100/AHD/JPEG references differ in aperture,shutter,motion and processing;they are qualitative references,not exact GT,and are not pixelwise scored. Captures/JPEGs/siblings remain excluded from training and original files read-only. [Main scene](../configs/gfx-qualitative-20231231.json) · [Fine cab mesh](../configs/gfx-green-mesh-20231231.json).

### All native comparison boards

mesh-seed2026112302-present-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-00.png)

mesh-seed2026112302-present-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-03.png)

mesh-seed2026112309-present-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-04.png)

mesh-seed2026112309-present-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-07.png)

mesh-seed2026112304-absent-iso6400-prior-RGGB;ROI `[165, 0, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-08.png)

main-overcast-sky;ROI `[176, 176, 160, 160]`,exposure4,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-09.png)

main-building-detail;ROI `[176, 176, 160, 160]`,exposure4,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-10.png)

main-foliage;ROI `[176, 176, 160, 160]`,exposure4,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-11.png)

main-chain-link-fence;ROI `[176, 176, 160, 160]`,exposure4,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-12.png)

mesh-nominal;ROI `[206, 229, 160, 160]`,exposure16,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-13.png)

mesh-nominal;ROI `[426, 189, 160, 160]`,exposure16,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-14.png)

mesh-profile3879;ROI `[206, 229, 160, 160]`,exposure16,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-15.png)

mesh-profile3879;ROI `[426, 189, 160, 160]`,exposure16,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-16.png)

organic-02a76fd33b5e1414a0504f0b3f0aeb03a569b6f4-photo-faint-RGGB;ROI `[112, 112, 160, 160]`,exposure14.3883,contrast8.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-17.png)

organic-dabacecd4780a1c230f8e9fce6ca1a604bdeab4c-photo-dark-RGGB;ROI `[112, 112, 160, 160]`,exposure102.758,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-18.png)

organic-6b3920bceba82d95ecf9351d47f6f94267694bd0-photo-dark-RGGB;ROI `[112, 112, 160, 160]`,exposure64.0491,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-19.png)

gray-l0.02-adc-only-RGGB;ROI `[48, 48, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-20.png)

gray-l0.02-iso12800-prior-RGGB;ROI `[48, 48, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-21.png)

flat512-gray-l0.02-adc-only-RGGB;ROI `[176, 176, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-22.png)

flat512-gray-l0.02-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-23.png)

flat512-gray-l0.02-iso12800-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-26.png)

flat512-h210-s0.50-l0.02-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-29.png)

flat512-gray-l0.18-iso12800-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure1,contrast8.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-30.png)

flat512-gray-l0.90-iso12800-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure1,contrast4.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-31.png)

photo-3e638bbb56ed80abc88939468783e3bf9b92ee77-photo-faint-RGGB;ROI `[176, 176, 160, 160]`,exposure12.1494,contrast8.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-32.png)

photo-3e638bbb56ed80abc88939468783e3bf9b92ee77-photo-dark-RGGB;ROI `[176, 176, 160, 160]`,exposure80.9959,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-33.png)

mixed-vertical-step-iso6400-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-34.png)

mixed-vertical-step-iso6400-prior-RGGB;ROI `[240, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-37.png)

mixed-vertical-step-iso12800-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-38.png)

mixed-vertical-step-iso12800-prior-RGGB;ROI `[240, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-41.png)

mixed-narrow-bar-iso6400-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-42.png)

mixed-narrow-bar-iso6400-prior-RGGB;ROI `[240, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-43.png)

mixed-narrow-bar-iso12800-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-44.png)

mixed-narrow-bar-iso12800-prior-RGGB;ROI `[240, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-45.png)

mixed-slanted-step-iso6400-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-46.png)

mixed-slanted-step-iso6400-prior-RGGB;ROI `[240, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-47.png)

mixed-slanted-step-iso12800-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-48.png)

mixed-slanted-step-iso12800-prior-RGGB;ROI `[240, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-49.png)

mixed-striped-patch-iso6400-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-50.png)

mixed-striped-patch-iso6400-prior-RGGB;ROI `[240, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-51.png)

mixed-striped-patch-iso12800-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-52.png)

mixed-striped-patch-iso12800-prior-RGGB;ROI `[240, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-53.png)

V150-control-bark-contrast0p025-adc-RGGB;ROI `[48, 48, 160, 160]`,exposure1,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-54.png)

V150-control-raccoon-fur-contrast0p025-adc-RGGB;ROI `[48, 48, 160, 160]`,exposure1,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-55.png)

V150-control-ADC-plane0-RGGB;ROI `[176, 176, 160, 160]`,exposure45,contrast8.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-56.png)

V150-control-ADC-plane1-RGGB;ROI `[176, 176, 160, 160]`,exposure9,contrast8.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-57.png)

V150-control-ADC-plane2-RGGB;ROI `[176, 176, 160, 160]`,exposure1,contrast8.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-58.png)

V150-control-ADC-plane3-RGGB;ROI `[176, 176, 160, 160]`,exposure0.24,contrast8.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-59.png)

### Noisy,restored,exact constructed GT triplets

mesh-seed2026112302-present-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-01.png)

mesh-seed2026112302-present-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-02.png)

mesh-seed2026112309-present-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-05.png)

mesh-seed2026112309-present-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure8,contrast1.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-06.png)

flat512-gray-l0.02-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-24.png)

flat512-gray-l0.02-iso6400-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-25.png)

flat512-gray-l0.02-iso12800-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-27.png)

flat512-gray-l0.02-iso12800-prior-RGGB;ROI `[176, 176, 160, 160]`,exposure4,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-28.png)

mixed-vertical-step-iso6400-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-35.png)

mixed-vertical-step-iso6400-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-36.png)

mixed-vertical-step-iso12800-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-39.png)

mixed-vertical-step-iso12800-prior-RGGB;ROI `[80, 176, 160, 160]`,exposure8,contrast40.

![Native comparison](images/v170-nonlocal-raw-v1/comparison-40.png)

## Reproducing dependency preparation

```bash
source scripts/env.sh
uv sync --extra nonlocal
PYTHONPATH=src:scripts .venv/bin/python scripts/fetch_nonlocal_raw.py
```

The optional comparison uses separately downloaded released weights and a local native kernel build. It is not selected by ordinary inference. [Independent publication verification](results/v170-nonlocal-raw-publication-verification-v1.json).
