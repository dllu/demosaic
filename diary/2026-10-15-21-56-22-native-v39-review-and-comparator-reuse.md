# Native V39 review and comparator reuse

V39 first1000 is complete and stopped. Compared with V37, native59/37 gives
known primary+.00903dB and unseen+.02932dB, both scene intervals crossing zero.
Full427 photo34.66049/.955174 versus34.65497/.955273: +.00552dB
[−.00996,+.01991], slightly lower SSIM. Procedural33.71264/.967447 versus
33.80809/.967787, - .09545dB[−.25382,+.02726]. One training seed; no broad gain.
FullGFX foliage/fence remain soft; no decisive visual improvement. New fullframe
35.28s, shared machine, not10s. Both new RGB16 TIFFs pass SHA/size, actual shape/
dtype/16bit tags, sampled-code and sRGB ICC checks. Ten matched160px native
triplets published; synthetic exactGT and real AHD/ISO100 references separated.

All33 logged Commons/paired input hashes match V37; native draws intentionally
change. All53 original native captures replayed exactly through old/new loaders.
Additionally compared source segments for native binning, phase alignment,
sample draw, length, degradation and domain selection: all6 match V37 byte-for-
byte. New sources do not overlap CanonM100/DMC-GH1 held-out camera models.
Source/camera/protected-scene admission remains separate from model selection.

Avoided repeated neural comparator work: evaluate only V39/classicals, retain
frozen V34/V37/RawNIND results with original report hashes. Model/numerical/
evaluation code and protocol/data identities match. Exact parity:24 known and30
unseen classical pair summaries, all37212 synthetic individual classical records.
This covers all443 sources/seven conditions/four CFAs before cached comparison
statistics are accepted. Composite labels0/1/2 mean V34/V37/V39; raw source
reports retain their own labels. New/cached V37 noisy/reference crop panels are
bit-identical, with matched source/ROI/noise/display metadata. No giant TIFFs or
neural baseline predictions regenerated. New-model full102MP inference still runs.

Initial reuse wrapper stopped on reference_input_scales: that field is populated
only when RawNIND itself runs, so new-only reports correctly leave it empty.
Inspected scope, retained the failed workflow/log, corrected the RawNIND-only
field check and resumed from the completed known-camera measurement, verified
by checkpoint SHA. That measurement was not repeated. All subsequent strict
classical parity checks pass. Archived source/workflow v2 and complete reuse
receipt live under the V39 run/evaluation roots; report and wrapper receipts
are in docs/results/native-v39-1k-review.json. Only2 new fullframe TIFFs written.

All304 tests/Ruff pass for the source version. Main is kept free of uncommitted
model changes. PackedV38 remains rejected; V34 real reference and V37 stronger
photo reference stay available. README remains representative V34. Next quality
work should correct the packed identity-noise bypass, not promote its speed.
Goal remains active: decisive qualitative SOTA/final test/new-model DINO ablation
and10s target have not been established.

Concrete next prototype: optional packed noise-aware detail prior, default off
for legacy checkpoint parity. ComputeHP=normalizedMHC−upsample(area2MHC).
Use144 impulses on a12x12 Bayer field to derive each color/output-phase noise
energy, retaining the four input-phase contributions for Gaussian WB ratios.
Central[6:8,6:8] has complete support. Store energy as a3D buffer to support
channels-last. GAT profiles use unitWB; Gaussian profiles use actualWB. Multiply
periodic output-phase variance by normalized noise². Local signal estimate is
max(box_mean(HP²,7)−box_mean(variance,7),0); Wiener gain is signal/(signal+variance).
Force gain1 at zero variance. Replace identityHP with gain*HP while retaining
native FP32 phase output/head and the coarse correction. Test allCFAs/odd packed
sizes/16bit ADC ramps, MonteCarlo variance, gradient/checkpoint/default parity.
Then compare phase-head/adapter LR1 versus10 with fixed pretrained-trunk LR3e-5,
same V34 initializer/seed47/batch16/original53 native data as V37/V38. This isolates
the architectural fix from V39's data change. No owned GPU training is currently live.
