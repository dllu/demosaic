# V159 final: modest coarse recovery with quiet and detail costs

Recorded: 2026-11-07T02:39:41-08:00 (America/Los_Angeles).

V159's fixed wider DC transition completes both1,000-update heads and full
four-endpoint review. Native512 noisy-flat full RMS falls0.27–0.39% and block32
0.17–0.19% versus V143. All48 coarse inputs improve at both endpoints against
V143,exact V158 and retained V156. Full RMS improves on46/48 raw and all48 EMA
inputs versus V143. Every full/block32 input remains worse than matched V157,
which has much larger quiet damage. Preserve V159 as a modest coarse/quiet
compromise alongside the other useful implementations.

Quiet total RMS rises0.18–0.48% versus V143 and0.28–0.57% versus V158,despite
spatial RMS falling0.33–0.55%. Original-pixel decomposition identifies mean
regional bias1.25–2.98% above V143. Raw/EMA worsen14/13 of32 quiet inputs;
maximum increases versus V143 are0.219149/0.224273DN16. Against V157,mean quiet
RMS is8.87–12.86% lower,but that uses its regressed baseline. V158 remains
stronger for quiet total/DC accuracy. Mesh response falls1.45–1.89% versus
V158 and2.34–2.83% versus V143. V156 remains stronger in learned response.
Natural fine response weakens;ADC-photo full RMS partly recovers0.72–0.83%
versus V143,while ADC sloped-field block32 worsens3.15–3.78%.

All72 primary figures were actually viewed in18 original-detail sheets. Crops
stay160px native,with identical ROIs/transforms and four retained V156/V157
columns on every board. Broad colored mottle persists;changes are modest.
Fine cab crossings remain missing under both priors/windows;foliage and natural
microtexture remain soft. Both standing real scenes include sky/building,
foliage/coarse fence,cab windows/priors and both SOOC JPEGs. Independent ISO100/
AHD/JPEG references differ in aperture,shutter,processing and motion;qualitative,
not exactGT,never pixelwise scored. Protected media/siblings stay out of training,
originals read-only,dataz unused.

Final CPU validation checks90 finite Adam states,four strict loads,exact complete
V158 control trace/raw/EMA/Adam. All1,644 actual control outputs replay exactly.
The immutable40-row preparation prefix stays historical. Original training and
review complete with all10 owners terminal,all stage returns zero,no restart.
There are5,364 actual scientific head evaluations:56 compatibility,20 discarded
smoke,2,000 production,3,288 review. New arrays4.422GiB are entirely external;
old evidence stays in place. V159 makes no parent/DINO/noise/source/RAW calls.
The separate coupled-noise construction has its own documented test/audit draws.

Noisy pre-clip median/max norms fall2.892114/357.251312→.102686/72.415810 and
clipped batches726→101/882. This confirms gentler optimization pressure,but
does not isolate a path or gradient component as the cause of a quality change.
All118 ADC batches retain zero gradient with all1,000 optimizer/EMA clocks.

Independent audit checks40,210 scalars over4,686 rows,max discrepancy4.55e-13,
with476 Decimal reductions and30 real rows unscored. Quiet DC audit checks160
outputs/480 scalars and energy identities. Publication preserves23 final receipts,
11 unchanged preparation receipts,33 source texts,87 neural hashes,12 additional
helpers,72 native PNGs and24 triplets. Final verification checks all source/
export/input/output bytes,14,745,600 retained V156/V157 RGB values,2,944 paired
entries and215 rounded numeric cells. Machine UTC and protocol/history preserved.

[Full report/native views](../docs/regional-dc-transition.md) ·
[Final receipts](../docs/results/v159-regional-dc-transition-final-v1.json) ·
[Verification](../docs/results/v159-regional-dc-transition-publication-verification-v1.json).

The first auxiliary final publication verifier failed on a generated report
locator,regional-smooth-dc.md. Its exact source and observed failure are preserved;
revision2 corrects the path and repeats full validation. Training/review and all
prior scientific receipts remain retained. A separate correction source records
this paragraph and the report note;the original final report builder is preserved.

Next direction is a fresh matched paired-response trial using the separately
tested sensor coupling. No paired training or quality gain is claimed yet.
Retain ordinary supervision and all quiet/coarse/real controls. Fine-detail and
clean-sky quality must improve together;the broader goal stays active.
