# Project goals and current evidence

**V120 Small is the current general restoration and quality-development choice.**
It reaches37.04008dB on all427 photos and54.31272/54.00872dB known/unseen
measured-CFA means, with tested ADC maximum55.52DN16. V114 remains a useful
Tiny alternative with lower tested ADC maximum51.73DN16; V115 has a slightly
higher known-camera mean and V117 a slightly higher photo score.
[Current choices](current-model.md) · [Completed primary/native review](v120-v121-primary.md).

The full [PROMPT](../PROMPT.md) objective remains active. Real foliage, finest
weak detail and dark-camera behavior still need work. The stronger released
RawNIND wins four of nine camera scene means; this small development set and
the GFX gallery do not establish broad real-camera superiority. Quality precedes speed.

The [V120/V121 data trials](paired32-weak-detail-training.md) completed their
original20k updates, numerical/native review and matched-profile complete-frame
comparisons. The [completed V122/V123 frequency trial](v122-v123-quality.md)
finds a real0.05493dB photo gain for the joint arm against adapter-only training,
with lower unseen-camera mean, a large ADC tail and little weak-detail recovery.
Both original20k budgets and numerical/selected native review are complete.
The [V124/V125 mean-loss trial](conditional-mean-training.md) has started V124's
two-noise-view control with frozen90,784-source/twenty-region inputs; V125 follows.
Successful implementation checks and source
cleanup alone do not establish trained quality gains.
The [completed V126/V127 shadow-data pilot](reviewed-shadow-pilot-quality.md)
shows no useful gain after1,000 matched updates; fixed-input metrics and native
comparisons are independently checked. Shadow exposure stays off by default.
The [completed V128 feature-loss pilot](v128-feature-pilot-quality.md) finds no
useful gain at1,000 matched updates, with independently audited native/GFX views.
[V129's completed curated27-region pilot](reviewed-detail-training-pilot.md)
finds small mixed changes without clear noisy/GFX recovery. The matched
[V130 FP32 pilot](training-precision-pilot.md) slightly improves selected faint-ADC
bands, with subtle native changes. The newest90781/29-region cohort has only
discarded [spatial-branch implementation checks](raw-spatial-features.md), with
no production quality result. The optional attention branch passes CPU/CUDA16+2
checks; a matched trained comparison remains necessary.

| Goal | Current evidence | Remaining work |
| --- | --- | --- |
| Excellent joint restoration | V120 photo37.04008dB; recovers V119's camera/color regression while retaining its photo score;427-source panels complete | Recover finest detail and reduce adverse cases before SOTA claims |
| Much better real-photo quality than RawNIND | Complete GFX frames/six regions and9 measured-camera scene means; supplementary11-capture binned-reference comparison favors joint-model detail | Reduce foliage/neon/fine-mesh loss and dark-field mottling; broaden evidence beyond these small development sets |
| 16-bit/full-resolution output | V120/V121 complete101.996MP FP32 outputs and linear/sRGB RGB16 exports verified, including matched-Haar full-frame comparisons | Preserve per-checkpoint precision/quality evidence |
| 100MP within10s on GB10 | Ordered Tiny/Small FP32 observations116.57/101.66s, not a controlled speed ranking | Target open; improve quality before speed work |
| Modern DINOv3 architecture | V84-family DRUNet and official frozen Tiny/Small pyramids; completed matched trained comparison | Retain useful gains and improve finer detail |
| Diverse clean targets and binning | V124 control training on90,784/twenty regions; completed90,786/14 and90,783/23,90,782/27 trials; prepared90,781/29 adds weak petal veins and sharp mesh;4×→geometry→area2, zero optical blur; actual reader/model checks | Train and assess the newest cohort; faint-shadow coverage and broad weak-detail recovery remain incomplete |
| Physical noise/camera/color | Poisson/read noise, signed black subtraction, all Bayer phases, WB/matrix and exposure/clipping; V120 ADC max55.52DN16, Tiny alternative51.73DN16 | Spatial dark-field/weak-detail failures and real-noise calibration limits remain |
| Resource-aware training and evaluation | Frozen source/parent/input plans and retained failures; V122/V123 full evaluation and selected native review complete; V124 training with original guards | Finish conditional-mean training/comparison and improve real-photo/detail quality |
| Protected originals/tests | Cached GFX3879/3880 and extra3842/3835 RAF/JPEG pairs; originals read-only; captures/siblings outside training;16-scene test reserve unscored | Preserve boundaries in future cohorts |
| Current documentation |54 completed primary endpoints in plot; native triplets, latest GFX comparisons and explicit profiles/checkpoints; local-time diary | Update useful results without promotion freezes |

The [V116 data review](v116-quality.md) is complete at its original20k endpoint.
Its matched Tiny control is V114; the original V112 initializer/seed/budget stay
fixed. All numerical/native/full-frame checks pass. Higher analytic eight-pixel
response does not yield broader weak natural-detail improvement; ADC color
tails worsen. A separate
[V114 eight-view pilot](v114-eight-view.md) is complete on24 saved observations,
improving selected material/camera scores with a color-bias tradeoff. Its full
panels/frame remain unmeasured; it does not close broad real-quality or speed goals.

Hot-pixel repair and [linear DNG/JPEG output](dng-export.md) are merged; repair
was off in these comparisons. Each improved-model report includes at least two
native noisy/restored/exact synthetic GT triplets. Separate ISO100/AHD RGB
references remain explicitly nonexact. [GFX gallery](gfx-qualitative.md) ·
[Version plot](performance-history.md) · [Historical evidence](requirements-archive.md).
