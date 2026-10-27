# Measure current-model gradient precision before a matched FP32 trial

Recorded: 2026-10-27T02:23:50-07:00 (America/Los_Angeles).

Completed a new fixed-weight training-gradient precision diagnosis at the current
V120 EMA, using eight retained training observations: two prior-selected source
strata, contrasts.025/1 and ADC/ISO12800.16 new differentiable native256/B1
forwards,16 reconstruction-gradient and8 FP32 normalized-band-gradient evaluations,
zero optimizer steps/new noise/RAW decodes. This is new V120 gradient work, not
replaying the older V112 parameter study. The old stored predictions/directions
are not forward inputs. Actual hidden-convolution dtype hooks distinguish BF16
and IEEE FP32; all weights/backbone/config/RNG state remain unchanged.

Most gradients are close in direction. The reviewed-region faint ADC case has
39.59% relative L2 difference, cosine.96124 and alignment with the same FP32
band-error gradient.35936 in FP32 versus.30952 in BF16. Other alignments are mixed;
the faint noisy photo is negative in both precisions. This is not an actual
AdamW step or evidence of trained quality. Independent NumPy/FFT audit reopens
all16 predictions, checks712 layer records and recomputes both retained faint-ADC
full gradient sets:534 arrays/197428224 FP32 values/1068 unique Gram entries.
Full raw vectors were not retained for the other six cases; dual live reductions
and hashes remain. Two mathematical tests pass. Standalone PNG/SVG/CSV/results
are published and the plot was actually viewed. Successful immutable execution:
training-precision-gradients-v2, plan7f233f018c9034f23419fac969e0ae7545f9bfc3ed97c3e31efa52181898528d,
collection881ab553bf4fea1827ad9bd86fcc43fa6dc39eb71437a154b652556f3fb21b9b.
Prepared-v1 was superseded for style before any forward; its zero-call receipt
remains. Actual B1 peakCUDA1338443776 bytes does not qualify B16.

V129 completed all1000 fresh curated-data updates and its86 candidate restorations.
Checkpoint5f17520fd68aed7865cd3094d77ec4368492cb67413df37a2787724ad19509c0.
All523 native/paired clean/noisy input pairs match saved V126; Commons changes
as declared. Domains477/262/261,1000 optimizer/64 validation/1064 encoder calls,
91 model/EMA tensors and89 Adam states finite. Reused old V120/V126 predictions;
no new noise/RAW. Independent audit passes240 metric rows/60 groups/3975 fields
and17203200 native PNG channels. All28 comparison boards were actually viewed
as seven unchanged848x768 sheets;13676544 sheet channels match originals exactly.
Published ten PNGs/4497408 exact channel values, including two exact synthetic-GT
triplets, main foliage/fence, and both correctedDSCF3842/DSCF3835 mesh regions
under both fixed profiles. Independent ISO100/binned-native references remain
approximate, not exact GT. Source attribution is retained in the manifest.

V129-V126 mean sRGB changes are+.0004212903dB shadow and+.0009292510dB ordinary;
cameraRGB changes-.0001213388/+.0005426513dB. No useful new native fur, foliage
or fine mesh recovery. This single-seed1000-update pilot does not rule out
longer training on the curated data. V120 remains the general recommendation.
README/current docs and both GFX galleries now reflect completed V129 evidence.

Started V130 IEEE FP32-only training versus saved V129 BF16 control. Everything
else is equal: V120 EMA parent, seed70,90782/27 data/quota.5,native256/B16,
singleview,zeroPSF,LR1e-5/warm100,paired32/native128 and all optional terms off.
Every1000 clean/noisy batch hash must match V129. Adopted the identical CPU FP32
18-update check only after full effective-config/training-source-byte proof;
original V129 receipt remains unchanged. New actual CUDA256/B16 check passed
16+2 updates, parent/resume identity, all18 input hashes,91 finite model/EMA and
89 finite Adam states. PeakCUDA11332900352 bytes. Fresh1000 production is running;
30min check/8h production,52GiB admission/16GiB CUDAcap/32GB runtime floor. No
automatic retry/reset or speed/quality claim. Its86-call quality queue reuses
V129/V120 controls. ADC-only heldout detail needs a separate evaluation before
concluding from this primarily high-noise panel.

An older collection execution schema lacks model_label. Initial V130 quality
preparation stopped before writing its plan or starting a controller; zero neural
calls. Preserved that preparation failure and made the label explicit in queue-v2.
Saved-control report wiring now supports both old/new schemas and V129 controls,
without relabeling old receipt bytes. A CPU-only attempt to reconstruct original
ADC packed inputs from reference-white targets found packed hashes unequal;
no baseline output was adopted and no neural calls were made. Exact operator
identity remains required for any ADC-control reuse.

V123's original bounded continuation and downstream chains remain in place;
no original budget, frozen membership or machine receipt was changed.

Publication verification passes10 unchanged copied PNGs/4497408 channels, all
315 current local links and17 frozen producer/dependent plans. Actual V130 production,
its quality waiter and original V123 continuation owners/children are verified.
Fifteen focused math/queue/retained-control protocol tests pass; Ruff passes.
