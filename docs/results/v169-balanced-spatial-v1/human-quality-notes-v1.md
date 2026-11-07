V169 removes broad displacement from V168's learned direct RGB correction while keeping its trained weights and spectral path. Mean quiet RMS falls **3.74–10.69%** and quiet DC color bias falls **11.45–31.59% versus V168**. Mesh response is essentially unchanged at **3.806–3.837% of constructed GT amplitude**. This retains V168's fine-wire response gain with less added quiet color bias, without retraining.

The tradeoff is measurable: **all 48 native512 coarse-flat errors worsen** at both endpoints, with means **0.529–0.770% higher**. Total-flat means rise **0.389–0.705%**. Quiet spatial error rises **0.167–0.267%**, with all32 raw and31/32 EMA cases worse. Native crops retain colored blotches and incomplete fine cab crossings. V169 is a useful quiet-color option with V168-level response; it is not a general flat-safety solution. V168 remains useful for coarse error, V165 for grain/total-flat error, V161/V164 for stronger learned response, V166 for quiet color, V158 for quiet accuracy and V157 for coarse capacity.

## What changed at fixed weights

Only the direct RGB correction is filtered. Its Gaussian lowpass at sigma8/radius24 native pixels is removed, with replicated boundaries; the parent image and spectral path are retained. The default filter preserves the tested 8px carrier to within .5% in the interior, and exactly removes constant corrections in FP32. It adds no learned parameters or persistent state tensors. All90 older neural files are unchanged. The 124,909 weights/47 tensors load strictly from the actual V168 raw/EMA exports.

The full branch ablations support a specific functional explanation at these weights. Spectral-only response is **3.730/3.765% of GT**, compared with **2.277/2.273%** for direct-only and **2.202%** for V143. Direct-only quiet DC bias is **13.05–46.26% above V143**, while its native512 full-flat means improve **0.567–0.979%** and coarse means improve **0.556–0.802%**. Much of its broad correction helps standalone flats and hurts quiet neighbors beside edges. Removing all direct RGB also loses useful fine correction; the balanced path retains more mesh response and lower full/coarse-flat error than spectral-only. This does not identify why training learned these corrections or establish performance outside this adaptive cohort.

## Quiet color improves; spatial mottle remains

Raw quiet RMS is **4.038576/6.336010 DN16** at ISO6400/12800, versus V168's 4.350000/7.094512. EMA is **4.046127/6.344343**, versus4.203388/6.745842. Raw improves26/32 quiet cases and EMA24/32. Quiet DC means become **2.018252/2.853456 raw**, **2.018205/2.853327 EMA**, only **0.106–0.154% above V143**, instead of V168's 13.05–46.41% excess.

Quiet total RMS still exceeds V143 by **2.98–3.78%**. Spatial error is worse than V168 on63/64 endpoint/input comparisons, despite lower color bias. Mean whole mixed-context RMS improves0.09–0.47%, which alone would conceal the residual quiet-region problem. A near-parent mean cast is not evidence that local splotches are absent.

Native512 full-flat means are **18.599781/24.189486 raw**, **18.618871/24.219097 EMA**. They worsen on40/48 raw and45/48 EMA inputs versus V168, and remain0.286–0.612% above V143. Coarse32 means are **13.436235/17.928281 raw**, **13.438463/17.930574 EMA**; their remaining mean gain over V143 is only0.011–0.032%.

Present-mesh full RMS rises0.138–0.248% to **8.953379/8.956287 DN16**, while signed response changes by just+.0240/+.0173% relative to V168. Actual blank RMS rises0.355–0.552%, to **5.601190/5.609300**. Wholly absent RMS rises0.297–0.534%, to **5.299300/5.305929**. Lower blank DC bias coexists with higher blank spatial error; a signed absent response near zero is not a safety guarantee.

All eight natural-photo cohort/endpoint full-RMS means improve versus V168 by only **0.0026–0.0199%**. Retained-source band error improves by less than .0006%; organic-source band error worsens by less than .0005%. These tiny differences do not establish better visible natural detail. All **72 ADC cases per endpoint** retain V168 outputs bit-exactly, including photographic and sloped controls. All48 constant-field outputs per method/endpoint remain exactly the parent; across four methods/two endpoints this is384 constant-field checks.

## Actual native review

All72 figures and24 triplets were inspected at original detail across18 sheets. Synthetic2302 remains almost flat despite the clear crossed GT; contrast40 mostly reveals broad mottle. Synthetic2309 keeps the strong diagonal family, with weak crossings still missing. Balanced and spectral-only look close at ordinary exposure, while the optional periodic correction recovers more lattice with direction/support defects.

The fine cab left crop remains largely erased; right keeps one direction more strongly than the crossing family under both nominal and profile3879 noise priors. No convincing new full crossings are visible. Main-scene coarse fence, building and foliage stay similar; ordinary sky remains smooth at exposure4. ISO100/AHD/JPEG references differ in aperture, shutter, movement and processing and are qualitative, not exact GT.

Quiet and dark-flat contrast40 panels retain strong red/blue/green patches. Overall color balance changes toward the parent, but localized false variation persists. Ordinary step/bar/pattern boundaries stay well defined. Bird, butterfly and plant microdetail remains heavily smoothed; ADC bark/raccoon detail and sloped planes look unchanged. The user goal of reliable fine crossings without false flat detail remains open.

The underlying V168 raw/EMA weight-export SHA256 values are `7e2be7ba5edadc2fbf8d97bf9cb275a7cec1714a5ea6ff61a8c2efcb1c118de2` and `d089b40e5502887510308816c648a9fc91d9cb58c687aa57862ed853e1efbc61`. The final manifest binds the new balanced-operator exports, source hash, fixed kernel, source ROIs, noise conditioning and display transforms. No target/reference enters inference.

The independent posthoc audit covers all replay/input/journal bindings,19,760 scalar comparisons and all saved native arrays; full new-array recomputation is limited to36 selected cases. All822 cases receive streamed metrics/fingerprints and independent in-process filter/norm checks. The two preparation/initialization corrections used no neural forwards; a resource pause resumed the same live worker without repeating inference. A pre-execution bookkeeping correction replaced ambiguous better/worse labels with decreased/increased for signed response fields. [Preserved correction](results/v169-reduction-label-correction-v1.json).
