The larger dense window gives a small mesh-response gain over V191, with a quiet-field cost. **It does not replace V187.** At the same 508-parameter / 900-update budget, response rises **1.72% raw / 1.50% EMA** over matched V191, to **4.556% / 4.540% of exact constructed GT amplitude**. Quiet spatial RMS rises **0.297–0.707% raw / 0.285–0.638% EMA**, worsening 31/32 cases in each state. Real fine cab crossings do not clearly recover. V187 remains the preferred experimental wave model; V120 Small remains the general recommendation.

All 103 neural source files are unchanged. V193 changes the large dense window, carrier grid and stride jointly from65/32 to129/64. Smaller33/17 supports, frozen matching65/32, coefficient units and native synthesis remain fixed. The V192 analytic SNR-support advantage motivated this test, but is not a learned-recovery bound or a quality prediction. These results do not establish a particular loss, capacity, support size or grid as the cause of remaining weak detail.

## Matched measurements

Relative percentages below compare means with the same V191 checkpoint state. Mesh has256 present and256 absent records; each quiet prior has16 cases and each fresh-flat prior24. These reused development cases are not blind validation or independent replications of every shared template.

| Measure | V193 raw | V193 EMA |
| --- | ---: | ---: |
| Present template gain | 0.04556243; +1.7200% | 0.04539934; +1.5030% |
| Present inputs with greater response | 200/256 | 181/256 |
| Present full RMS, DN16 | 8.865485; −0.09184% | 8.866280; −0.08316% |
| Present blank RMS, DN16 | 5.615258; +0.01072% | 5.614576; +0.00929% |
| Absent full RMS, DN16 | 5.311882; +0.01015% | 5.311444; +0.01058% |
| Quiet spatial RMS, ISO6400 prior | 3.491537; +0.70749% | 3.488467; +0.63819% |
| Quiet spatial RMS, ISO12800 prior | 5.618848; +0.29687% | 5.618571; +0.28482% |
| Fresh-flat full RMS, ISO6400 prior | 18.616724; +0.00603% | 18.613300; +0.00130% |
| Fresh-flat full RMS, ISO12800 prior | 24.186112; +0.00965% | 24.181644; +0.00178% |

The present full-RMS means improve although only121 raw /113 EMA of256 individual cases improve. Blank errors worsen on234 raw /236 EMA present cases; absent errors worsen on250/253 of256. Signed absent template gains are −0.00002262 raw /−0.00002503 EMA; no percentage is formed around a near-zero signed baseline. Fresh-flat full RMS worsens on46/48 raw and34/48 EMA inputs. Coarse32 RMS means are mixed and change by less than0.0008% versus V191. Quiet DC means improve slightly, while quiet total and spatial error rise; small DC changes do not cure mottle.

Natural fine-band response rises in three of four raw group means, with changes from−0.00038% to+0.06519%; EMA improves two means and loses two, from−0.04202% to+0.03972%. Raw band-error means are mixed; all four EMA band-error means worsen by0.00056–0.00417%. All four natural-response means remain below same-state V187. These are small measured differences, without a statistical-significance or blind-generalization claim.

Against preferred V187, mesh response remains **12.838% raw /15.286% EMA lower**, with179/198 of256 cases losing response. Raw quiet spatial means worsen0.730% /0.116%; EMA worsens0.340% at ISO6400 and improves0.0548% at ISO12800. EMA fresh-flat full-RMS means remain0.0074–0.0170% lower than V187, but absent errors are higher. Against the actual frozen V183 EMA initializer, mesh response rises2.641% raw /2.274% EMA, with quiet spatial means0.421–0.847% higher. The larger dense implementation has a real limited response gain over V191, alongside weaker quiet performance; no baseline is promoted merely because this trial completed.

## Actual native inspection

All60 figures, including12 noisy/restored/exact-GT triplets, were viewed in15 original-detail sheets and15 focused sheets. Every cell retains160×160 native pixels. Mesh2302 remains weak at the common40× contrast stress transform; changes from V191 are subtle and its fine modulation is weaker than V187's. Mesh2309 retains its strong direction while the weaker crossings remain incomplete. The aggregate response gain does not demonstrate complete two-direction recovery.

The protected main scene retains sky, building, foliage and coarse chain-link fence. Sky looks smooth at exposure4; building and foliage remain soft, and the coarse fence survives. Both fine cab ROIs under both noise profiles show no convincing new crossings. Independent ISO100/AHD and both straight-out-of-camera JPEG references retain visibly stronger mesh, but differ in aperture, exposure, motion and processing. **They are qualitative references, not exact GT.** No pixelwise real-reference score is reported.

Natural bird, butterfly, bark and foliage details remain soft. Stressed gray/blue/mid/bright flats and quiet step/bar/slant/striped contexts retain broad colored mottle and false directional modulation. There are small fine-pattern changes, without a visible cure. ADC bark, fur, uniform fields and four planes retain the inherited output exactly.

The two constructed mesh triplet sources are `mesh-seed2026112302-present-iso6400-prior-RGGB` and `mesh-seed2026112309-present-iso6400-prior-RGGB`. Each uses native512 RGGB input, ROI`[176,176,160,160]`, shot0.00128/read variance6.5536e−6, exposure8/contrast1. Stress boards use the identical pixels at contrast40. Fine cab context is`[600,6260,768,768]`, with ROIs`[206,229,160,160]` and`[426,189,160,160]`, common exposure16. The manifests bind each cached source, white balance/matrix, actual supplied variance and display anchor. Crop pixels are never resized.

Final source checkpoint SHA256 is `c4a60ffbda0635f7503888d9c02957867d328138dc6918eebfacd6f32609f8d8`. Raw module SHA256 is `142c77d4b1092c4ec2b934889d0746e91fffed13e2ab13beebbd1c8a32e4ce64`; EMA module SHA256 is `1135b23012ae54167565abaee7ac08fc4cdaf16f0dc054b37c66be105c425e1a`. The publication index binds each strict export and separate viewer state.

## Execution and limits

Fresh V183 EMA initialization,1,000 cached rows,900 updates,3,600 images,100 ADC skips, nine losses/masks/domain weights, schedule, clipping and zero head Adam/EMA clocks match V191. The run completed once with genuine row8-to9 restoration and five checkpoints. Full training and quality audits pass, including1,644 exact replays each of V183 EMA and V169,144 ADC outputs,72 native RGB plus72 wave arrays,53,772,288 native addition channels and510 recomputed native metric scalars. Independent QR samples check1,080,000 real coordinates across all750 noisy input contexts. Full-field hashes bind execution and raw/EMA equality, not full-field QR recomputation. The31-method comparison retains25,482 rows,58 contrasts and2,226 cells.

New checkpoints/native arrays/exports/browser captures use external SSD scratch with a0.70GiB forecast above110GiB floor; local sources/receipts/figures/publication use0.25GiB above40GiB floor. RAM32, launchRAM52 and CUDA quota24GiB remain recorded. Both protected GFX captures/JPEGs/siblings remain held out; originals and unavailable dataz are untouched. No new source/noise draw, RAW decoding or parent/DINO inference occurs. All prior neural sources, checkpoints and machine evidence remain preserved. Fine-real-crossing, flat-field and102MP speed goals remain open.
