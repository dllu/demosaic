V185 is a useful incremental update to the direct wave readout: **more weak-mesh response and less quiet-field error than V184 at the same new-head training budget.** It still leaves false fine striping, broad colored mottle and incomplete real cab-fence crossings. It becomes the current experimental wave-readout option; V120 Small remains the general recommendation. No new full-photo speed result or broad benchmark establishes a replacement for that model.

## Matched measurements

These are relative changes of paired-suite means, raw versus V184 raw and EMA versus V184 EMA. Each endpoint uses the same 822 fixed development inputs; the suite has been reused during development.

| Measure | V185 raw | V185 EMA |
| --- | ---: | ---: |
| Present mesh signed response versus matched V184 | +2.10975% | +0.45256% |
| Absolute response as percent of exact constructed GT | 4.96761% | 5.17091% |
| Present mesh whole RMS | −0.07975% | −0.00352% |
| Present mesh blank RMS | +0.00424% | −0.00150% |
| Absent mesh whole RMS | +0.00322% | +0.00133% |
| Absent mesh crop spatial RMS | +0.01630% | +0.00507% |
| Quiet total RMS, ISO6400 / ISO12800 | −0.42278% / −0.33588% | −1.03108% / −0.66256% |
| Quiet spatial RMS, ISO6400 / ISO12800 | −0.54732% / −0.41930% | −1.37533% / −0.83327% |
| Standalone flat whole RMS, ISO6400 / ISO12800 | +0.00192% / +0.00289% | +0.00096% / +0.00133% |

Mesh response increases in 170/256 raw and 138/256 EMA inputs. Whole-mesh RMS improves in only 91/256 raw and 71/256 EMA inputs despite the lower means; the mean improvement is uneven. Quiet spatial RMS improves in 25/32 raw and **all32 EMA** inputs; quiet total RMS improves in27/32 raw andall32 EMA. Quiet DC also falls slightly. Standalone flat whole RMS worsens in47/48 raw and43/48 EMA inputs. Absent-mesh whole RMS worsens in254/256 raw and225/256 EMA inputs. Signed absent gains are1.1998e-5 raw and1.1006e-5 EMA; no relative percentage is assigned to these near-zero signed quantities.

Natural fine-band response rises in all four cohort/contrast means: +0.01261–0.06975% raw and +0.00378–0.02318% EMA. Relative band-error means worsen in three of four raw groups and one of four EMA groups; 68/128 raw and62/128 EMA individual band errors worsen. This is a small response change, not universal detail recovery.

Against frozen V183 EMA, mesh response is +11.9081% raw / +16.4881% EMA, but quiet spatial RMS remains **+0.3425–0.3836% raw / +0.9386–0.9585% EMA**. Smaller support recovers part of V184's quiet cost rather than removing it. Versus V180 EMA, response is +9.2160% raw / +13.6858% EMA, while quiet spatial RMS changes −0.1099%/+0.2528% raw and +0.4424%/+0.8682% EMA at ISO6400/12800. V161 harmonic EMA retains more mean mesh response: V185 is −5.1957% raw / −1.3157% EMA, while quiet spatial RMS is lower by5.05–7.86% onall32 inputs. All23 methods, including V173's quieter alternative, remain in the complete tables and native boards.

## What was actually visible

All60 native figures were viewed in15 original-detail sheets, then journaled. On mesh2302, the normal display remains almost uniform; contrast40 reveals stronger fine periodic modulation on a broad colored field, far from the exact target lattice. Mesh2309 still loses the weak crossing orientation. V185 versus V184 changes are small. In absent mesh and dark standalone flats, broad green/purple blotches persist. Normal gray and bright flats look much smoother than their amplified views.

The protected main scene retains a smooth-looking sky at exposure4, coarse chain-link strands, and soft building/foliage detail. For the difficult green cab mesh, both fixed ROIs and both nominal/main3879 noise profiles remain soft and incomplete. Small changes in strand contrast do not establish clearly completed new crossings. Bird feathers, butterfly markings and bark also remain softer than constructed references.

Quiet steps, narrow bars, slanted edges and stripe patches retain false fine vertical/diagonal modulation atcontrast40, with some faint banding atnormalcontrast. Some modulation is reduced relative to V184, especially EMA; broad casts remain. Exact ADC bark, fur, gray and sloped-plane controls stay inherited. This does not establish clean noisy skies or absence of hallucinated detail.

## Architecture and execution

The [implementation and preparation](spatial-context-wave-readout.md) retain the65-packed-pixel wave basis and the same selected bins. Two additional33/17-packed-pixel windows atstride8 provide12 context channels. The head grows316→508 parameters (18→16→12); old six hidden input weights/bias are copied exactly, extra inputs and final mixing start zero. All189 V183 EMA tensors remain frozen/eval. Overlapping RAW measurements reuse noise; they are not calibrated confidence or independent evidence tests.

A fresh900-update run uses V184's same1,000 cached rows,3,600 noisy images,100 ADC skips, allnine losses, clean masks, domain weights, learning-rate schedule and head EMA clock. The extra192 parameters and additional spatial context change together. Genuine row8restore resumes9 without replay. Five factored checkpoints retain raw head/Adam/EMA/RNG and bind the immutable V183 initializer; all reconstruct193 strict tensors. Training peak allocation6.22351GiB; review2.78617GiB. The 100MP/10-second objective remains open.

Original training and review are terminal. The training audit checks all900 FP32 nine-term totals/masks/clocks and1,890 inherited-tensor comparisons across five checkpoints. The quality audit checks6,576 input fingerprints,1,644 V183 EMA and1,644 V169 exact replays,144 ADC outputs,750 equal raw/EMA input-evidence pairs and750 equal support-fingerprint pairs. It independently decodes72 RGB and72 wave arrays, checks53,772,288 ordered baseline+wave channels,510 ordinary native metric scalars plus72 wave RMS scalars (582 total),278 Decimal summary means and378 inherited-tensor comparisons. Reduction retains23 methods/18,906 rows/42 contrasts/1,554 table cells,3,147 Decimal means and15,540 paired mean/difference checks. Rendering independently checks8,294,400 new and72,883,200 unchanged displayed RGB channels. No old scientific inference was rerun.

Native arrays are lossless: checked FP32 addition recipes reference immutable V183 RGB and compressed waves, with XOR fallback when necessary. No bits are quantized, including signed zero. Native storage is130.434MiB for144 arrays, versus410.25MiB of uncompressed array bytes. Journals and full paired tables use losslessgzip. Completed duplicate arrays, source snapshots and receipts share storage while retaining every original path and content hash; original captures, caches, checkpoints and machine receipts retain their bytes.

## Crop, checkpoint and reference metadata

The representative triplets are fixed mesh seeds2026112302/2309,512×512 RGGB contexts, native ROI`[176,176,160,160]`, shot`.00128`, read variance`6.5536e-6`, exposure8, contrast1. Contrast40 boards use the same pixels and transforms across methods. Quiet ROI`[80,176,160,160]` uses exposure8 and contrast40 about camera RGB`[.001500000013,.006000000052,.002666666871]`; ISO12800 uses shot`.00256`, read variance`2.62144e-5`. Every160×160 crop is unresized. The manifest carries each complete input/source/ROI/noise/display binding.

Training checkpoint SHA256: `4bce120381d4c5208e17f10e43a450b0e00884dcbb8f6a7b632312a714787d9f`. Raw module-state SHA256:`485b7b36d61586f3a10c588f88945037cc180b3e8e30633f08ba14a0081deaa9`; EMA:`6a7e4fa774520ad2e3437d7ec4330c4b2d5e4b006bf6e1bca4054c66e47b668b`. The factored checkpoint binds the immutable V183 EMA initializer export`b713608498158b24b09da72c8079d6eae58bc2458f7d4ac63d493b7b679f63b3`. Both full strict exports and all14 viewer states have separate checkpoint/state metadata.

Main GFX inputs are cached DSCF3879 ISO6400 and DSCF3880 ISO100; sky/building/foliage/coarse-fence crops remain in the report. Cab inputs are cached DSCF3842 ISO6400 and DSCF3835 ISO100, with both SOOC JPEGs, context`[600,6260,768,768]`, ROIs`[206,229,160,160]`/`[426,189,160,160]`, exposure16. ISO100/AHD/JPEG panels are independently processed qualitative references, **not exact GT**: aperture, exposure time, motion and processing differ. Captures/JPEGs/siblings remain excluded from training. No originals or unavailable dataz were accessed.
