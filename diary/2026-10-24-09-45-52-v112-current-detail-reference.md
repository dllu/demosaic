# Refresh current detail and stronger-reference camera comparisons

Recorded: 2026-10-24T09:45:52-07:00 (America/Los_Angeles).

Previous goal turn was progress: bf5edf8 completed actual matched V112 CPU
updates for the optional fine source, with saved-array checks. It did not
establish a trained-quality gain. This turn confirmed original training
867877/1792848017.25 and both exact waiting reviewers live before analysis.

Found the main heldout-detail page still called V104 the working baseline and
V111's full-photo result pending. Refreshed it with V112's existing scores and
native comparisons, preserving all earlier explicit-version evidence. Added
the current V112 column/row to the stronger-reference material/camera tables,
updated V112's actual Tiny/Small execution status and linked the current
higher-noise gallery from README. No model or inference policy changes.

Reused the original twelve material cases, all162 camera crop scores and
already-published native triplets. No model/encoder forward, new noise,
optimizer update, RAW decode or CUDA work occurs. The plan fixes all four
material sources/three conditions, all nine development scenes and the two
earlier stronger-reference native examples (bark/fur). No reserved scene is
scored, no new output-based example selection is introduced, and no existing
receipt or executed source is overwritten.

V112's selected material means are39.74086/40.90266/33.51165dB at ADC-only/
ISO100/ISO12800, versus pre-upsampled RawNIND28.13487/28.12808/27.59760.
All12 source/condition cases improve, with high-noise difference+5.91406dB.
These are four selected synthetic-source means, not the full427 benchmark
or broad real-camera evidence. All original V104 metrics replay exactly
through the material bridge between the two execution sets.

Matched camera prepared-manifest hashes, scene/capture/tile/ISO/CFA identities
and measured-reference sample counts across every crop. Mean nine crops per
capture, two captures per scene, then scenes. V112 exceeds stronger RawNIND
by only+.00846dB known /+.08850 unseen, improving2/4 and3/5 scene means.
It still loses on D60-2−.11473, MuseeL-CopteArch-C500D−.54382,
LucieB_Coulicoco−.46431 and LucieB_top_of_Expedit−.16024dB. The per-scene plot
shows these gaps alongside V104; small gains over V104 do not eliminate them.
Exact empirical scene-resampling95% intervals enumerate4^4=256 and5^5=3125
samples: [−.38377,+.41835] /[−.24883,+.36799]. They describe this fixed small
scene set, without training-seed uncertainty or a general winner claim.

Independent stdlib fsum/manual-quantile arithmetic reproduces every scene mean
and interval with maximum discrepancy0. All162 historical V104 control crop
rows replay exactly. Full V112 camera float predictions were not retained in
the original evaluation, so this validates aggregation and joins, not a new
reconstruction of metric definitions from floats. Future endpoint archives
retain those predictions. The protected16-scene reserve remains unscored.

Composed one new native board directly from original RGB8 triplet cells:
noisy, stronger RawNIND, V112 and exact synthetic GT for bark and fur. All eight
160px cells match original pixel bytes. Noisy and GT cells match across methods;
ROI[48,48,160,160], exposure1, shared WB/matrix, RGGB and ISO12800 shot.00256/
read variance2.62144e-5 stay fixed. The board and camera plot were actually
viewed at original resolution. V112 retains more bark grain and fine hairs
than the stronger reference, while GT still contains missing texture/hairs.
Both original V112 high-noise triplets are also shown in the current gallery,
with full source/weights/conditioning/display/credit links. Historical PNGs
and machine receipts retain their original bytes.

The largest individual camera deficit merits a subsequent native diagnosis:
MuseeL-CopteArch-C500D:eaeee7bf990cc88c2d0809b5df1cad25965bc526fd411ac97edef5224e97914a:2506:2128
is−4.70361dB versus stronger RawNIND. Its other-capture same-location deficit
is−4.03894dB. These scalar deficits do not identify signed bias, noise,
registration or texture as a cause; full outputs are needed to distinguish
them. This is a prospective diagnosis, not new neural execution this turn.

[Current native gallery](../docs/heldout-detail.md) ·
[Current stronger-reference camera differences](../docs/rawnind-variants.md#current-v112-camera-comparison) ·
[Source joins, independent checks and original native pixels](../docs/results/v112-strong-reference-current-v1.json).
Private plan, worker, output, independent arithmetic/pixel auditor and logs:
.cache/current-quality-20261023-v1/V112-strong-reference-review-v1/.
V112 remains selected; V114/V115 continue their original frozen budgets and
review chain. Broad real-camera superiority and100MP/10s remain open.

Final verification at 2026-10-24T09:52:31.148038-07:00 checks 141 bound files,
130 local links and all three current frozen training/review plans.
V112 selector/checkpoint remain exact. Training867877/1792848017.25 is live
with V114 at logged step14500; evaluator986158/1792855221.87 and
audit986159/1792855223.35 are live/waiting with no children or completed stages.
No existing source, budget, receipt or successful learned evaluation is repeated
or changed. Source/model tests are not repeated for these documentation and
retained-pixel/statistics changes.
