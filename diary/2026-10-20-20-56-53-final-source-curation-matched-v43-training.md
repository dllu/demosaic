# Complete Commons source review and queue matched V43 quality training

Recorded: 2026-10-20T20:56:53-07:00 (America/Los_Angeles).

The original full-source V43 scoring worker completed all 88,508 training
sources: 177,016 fixed ADC/ISO12800 cases and 22,128 actual neural/DINO forwards.
It was never restarted during the supervisor handoff. Worker and supervisor
identities are confirmed exited. The final receipt is
`4db349cb6730c9cb5cfd4a70a76345711bb7da31e1fe658411b6a9ea0556cc57`.
An independent streaming audit verifies every source/condition, finite metrics,
the original loss arithmetic, ROI bounds, source/cache declarations, score-file
hash and owner exit. Its receipt is
`51bbf1afd62c1cccc34c6f57f32945042642df6e28cc529e5828dfefd6d53bd6`.
The executed worker separately records model/DINO/config/parameter/RNG/input
invariants. This does not freshly whole-hash all corpus originals/caches.

Actually viewed five final native contact sheets and one larger native1024
turtle crop, adding 25 unique sources. Retain 24: physical stained glass,
painted/tiled architecture, circuit boards, engraved metal, sand, speaker mesh,
faint skies, haze and rainbow slopes. Withhold the flat stippled turtle
illustration, without inferring a digitization or generation pipeline. Across
all rounds, 371 sources were actually viewed: 347 retain / 24 withhold, using
68 sheets and 27 larger native views. All 87 distinct required sources from the
completed top32-per-condition/top16-per-proxy ranking have decisions; the
previously completed recorded-ISO>=12800 subgroup remains 66 retain / 8 withhold.
This is targeted review, not a full-corpus manual inspection or defect-rate
estimate. Final-round receipt:
`291abecb8ede5c81b1070e25fab4504443ad1771e5484ddb3f9241995bb7ea75`.

The first strict membership-freeze attempt stopped before creating any output:
four early larger-view decisions lacked explicit source/cache hash fields.
Their original immutable render indexes already held those identities. A new
ledger restores only missing identity/native-view fields, freshly whole-hashes
those four originals/caches, and preserves their decisions, reasons, view
references and all older evidence. Backfill receipt:
`e2f3d7d78f8dd803fce2de72e80a61130c8443a9a0ea6fd27b2b569154715c10`.
The identity-complete public ledger is
[source-quality-visual-review-v17.json](../docs/results/source-quality-visual-review-v17.json).

The subsequent strict freeze succeeds at
`.cache/quality-first-20261020/curated-corpus-v1/`:

| Cohort | Train | Validation | Test | Manifest SHA256 |
| --- | ---: | ---: | ---: | --- |
| Original eligible/curated intersection |39,983|2,303|2,255|`717575f4d410f3ef8256b003ada29e95e31a543ea15b705ca5406d19ed48a13b`|
| Larger eligible/curated |88,484|2,303|2,255|`36ae0b55938c2cf52676cf82845e3eba6394bc95195c7a7b8822f8bd5a8e1ed2`|

Of V43's original 40,170 training IDs, 172 are already ineligible under existing
corpus policy and another 15 are among the 24 newly withheld sources. The larger
cohort adds 48,501 training sources over the control. Independent membership
recomputation checks every selected full record, exact current holdout records,
original val/test IDs, all exclusions, and absent standing GFX filenames.
Protected/series exclusions remain inherited; originals/historical manifests
are unmodified. Curation receipt:
`a44ffef5b142f2394f3e9f299f505b446a9880c168ff6db6d2fc00083d1998ab`;
independent membership audit:
`a2b7fb4bef2a7dcfb3d2ec870210a205a20126a0753f23827a80877f033f767f`.

Prepared and queued the real matched V93/V94/V95 study at
`.cache/quality-first-20261020/V43-curated-matched-training-v1/`, plan SHA
`2fec2f3e77e15791d1ece4e10e65133a84be234eba0702a4d4dcd643753f7556`.
Artifacts use the fresh owned external namespace
`/mnt/external/demosaic/v43-curated-training-20261020-v1`.
All three start from the same original V43 step2000 EMA, with fresh optimizer
and common seed56/B16/native256/20k schedule. V94 changes only Commons membership
versus V93; V95 changes the optical-blur/weak-detail augmentation package versus
V94. Fresh discarded CPU24 and CUDA24 checks for every arm precede production.

Controller PID2355916/create1792554876.82 is queued for stable headroom:
48 GiB available RAM for60s, system64/external384 GiB free, with a two-hour
per-stage resource wait. Only about11 GiB RAM was available at launch, so no
child/preflight/production update has run at this snapshot. Other workloads
remain untouched and resource bounds are unchanged. Stage failures retain
evidence and do not automatically retry. Final20k EMA is primary; validation
best and4k/8k/12k/16k diagnostics remain separate.

[Public completion/plan receipt](../docs/results/v43-quality-curation-and-training-plan-v1.json)
records these inputs and the immutable launch observation. Live `status.json`
can advance. Updated the quality plan, illustrated source-review guide,
validation guide and experiment index. V43 remains the working reference; this
establishes no new model-quality, speed or promotion result. Full independent
quality evaluation and actual native crop inspection remain required.

