# Review matched V43 primary quality and extend the history plot

Recorded: 2026-10-21T15:49:47-07:00 (America/Los_Angeles).

All three final 20k arms have now completed the full primary panels. The photo
branch covers 427 photographs plus 16 separate procedural sources, seven
conditions/four CFAs and nine methods: 111,636 score records. Known/unseen panels
cover all 4/5 scenes, 8/10 pairs and 72/90 crops, with 648/810 score records.
Independent coverage, validity support, source/scene aggregation and paired
bootstrap arithmetic pass; maximum summary discrepancy is 7.11e-15.

Fresh FP32 primary means are:

| Model | Photo sRGB PSNR | Known CFA PSNR | Unseen CFA PSNR |
| --- | ---: | ---: | ---: |
| V43 | 34.89933 | 54.23334 | 53.80629 |
| V93 | 35.24714 | 54.28970 | 53.70392 |
| V94 | 35.25352 | 54.30619 | 53.62349 |
| V95 | 35.29553 | 54.33307 | 53.76990 |

V95 minus V43 photo gain is +0.39620 dB, paired 427-source interval
[+0.32633,+0.45182]. Larger membership alone (V94 minus V93) is +0.00637 dB,
interval [-0.00955,+0.02475]; this study does not establish a photographic
membership benefit. The augmentation package (V95 minus V94) adds +0.04202 dB,
interval [+0.02328,+0.05885]. V95 improves the known-camera mean by +0.09973 dB;
its unseen mean is -0.03639 dB, interval [-0.23642,+0.14168]. These intervals
resample sources/scenes, not independently trained models; this is one seed.

Complete and independently audit the analytic branch: all 2,240 case rows,
140 groups and 3,760 scalar fields, with maximum discrepancy 2.23e-16.
The 2%-contrast four-pixel ADC-only gain rises from V43's 0.489/0.350 to
V95's 1.052/1.027 at the two backgrounds; ideal gain is 1. The brighter 2% 16-pixel
high-noise gain rises from 0.241 to 0.615, and high-noise flat spatial RMS falls.
Actually view all three preselected native carrier/flat cases. The bright weak
carrier is visibly stronger in V95; the shadow high-noise eight-pixel carrier stays
largely suppressed. This is a fixed analytic diagnostic with repeated ADC
observations, not proof of all natural texture recoverability.

Also actually view both preselected real cases per camera panel. The joint
methods preserve plate/chart geometry better than the RawNIND adapters, while
the independently demosaiced references retain noise/AHD artifacts. Some V95
fine flecks are more visible, but the reference does not establish every fleck
as scene detail. Native board hashes and observations are retained privately.

The color stage finishes, followed by both GFX stages. Independently reconstruct
all 1,176 color observations/4,704 saved float predictions, 28,224 Torch64
scalar fields and all 12 native triplets; maximum difference 5.56e-16. A separate
72-group/864-field audit differs by at most 8.68e-19. Actually view all three
preselected native uniform-color cases. V95 improves ADC-only color tails,
but ISO12800 p95 max channel-mean bias rises from 0.002569 to 0.005206 and worst centered
RGB RMS rises from 0.002559 to 0.004058. V93/V94 magenta fields look cloudier; V95 is
closer to V43 but retains extra nonuniformity. Preserve this unfavorable tail.

Actually view all four standing GFX regions and both highlight contexts for
all six methods. V95 fence wires and some foliage edges appear a little crisper
than V43; differences remain modest. Its blue-neon variation cannot all be
called recovered true LED detail. All four joint models give cleaner building/
fence geometry than RawNIND here. DSCF3879/3880 remain locally cached and outside
training; ISO100/f5.6 is a separate qualitative reference, never exact GT.
No full-frame output or speed trial occurs in this evaluation.

All seven stage owners and the controller exit. Bind the full plan, report and
result hashes, conserved model/DINO/configuration/RNG checks, sampled physical
inputs and actual native-view records. Counts total 17,824 joint forwards/DINO
calls. Every one of the 96 saved triplets is represented in actual native views;
there are 132 distinct 160-pixel cells after sharing identical noisy/reference
panels. Detailed complete-review SHA:
`c41d08b696dfd694dfedf6da8090282fec5911e9d21d4162ed25a65c957637be`.

Publish the [complete review](../docs/v43-curated-original20k-review.md), primary
statistics and complete review receipts. Copy eight native photographic
triplets (two per joint model) and twelve V43/V95 GFX triplets byte-exact with
their source/ROI/checkpoint/noise/exposure sidecars; include unchanged analytic
review boards. Keep real references accurately labeled.

Extend the [version history](../docs/performance-history.md) to 35 selected
endpoints. The collector accepts hash-bound report references as well as
embedded summaries; all 32 historical points remain exact and all three new
points match completed primary reports. Generate PNG/SVG/PDF and CSV/JSON,
view the plot, and replace hardcoded counts/tight latest-version ticks. These
are descriptive unequal-budget/architecture results, without model inference.

V95 is a promising next quality candidate, with clear measured weak-detail
progress; keep V43 as the working reference while addressing saturated
high-noise color tails and unseen-camera uncertainty. The next quality target
is that color behavior while preserving the detail gain, under the same V43
architecture. Speed stays deferred. This does not establish SOTA, broad unknown
scene superiority, V95 full 100 MP qualification or the 10-second requirement;
the full PROMPT goal remains active.

