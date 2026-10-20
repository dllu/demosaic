# Capture metadata review and external training artifacts

Recorded: 2026-10-20T13:15:11-07:00 (America/Los_Angeles).

The training-only capture-header inventory completed all 88,508 sources. It
records positive ISO for 82,094, with 1,370 at ISO3200 or above. Two threads and
32 pending futures read JPEG/MPO first-frame headers; pixel loading is forbidden,
torch is not imported and CUDA is hidden. Independent checks verify unique ID
coverage, manifest/operator/output hashes, counts and both owners' exit. EXIF
warnings remain in the log; zero exception records does not mean complete EXIF.
No GPS is extracted and no fresh whole-original hash claim covers the whole
inventory. The selected-view renderer separately verifies originals and caches.

The initial v1 preparation was unused. V2 stopped after40 rows on a valid MPO
because its JPEG-only assertion was too narrow; that failure/log remain, both
owners exited, and a newly frozen v3 added MPO and bounded pending futures.
Successful v3 plan SHA256:
`71fa15cbcc7ced70f18976fae8e68411dc475c272825ecb2d9580d7a598b4c3e`;
receipt `556a834b9e0920daf00605f596ada1e4de5dcdc2a37d21bc8a379b53a6877d8c`.

Actually viewed three native contact sheets for sixteen previously unreviewed
sources: eight highest recorded ISO plus eight deterministic hash-selected
high-ISO sources. Also viewed five larger native1024 crops. Withhold four bird
images with pronounced etched/flattened feather structures and enhanced edges
remaining in their binned targets; no exact filter or synthetic origin is
asserted. Retain twelve, including high-ISO wildlife, water drops, portraits,
architecture, lettering and railings. ISO/software tags are review cues only.
The cumulative review is222 sources /204 retain /18 withhold, from42 sheets and13
larger views. Private decisions are
`.cache/quality-first-20261020/manual-source-quality-decisions-v10.json`;
public summary is [visual review v9](../docs/results/source-quality-visual-review-v9.json).
This targeted sample does not estimate the corpus defect rate or replace final
top-loss/proxy review. Originals and historical memberships stay unchanged.

The training launcher now accepts a fresh external artifact namespace via
`--artifact-root`. Checkpoints/traces use the external SSD; frozen plans/code
stay local. A new prospective external-artifact plan fixes root64/external384 GiB
free-space reserves. Default local-artifact plans keep64/500. A preparation-only
CPU/provisional check verifies the owner marker, all three destinations and
frozen source/input guards, with no controller/checkpoints/CUDA/training launched.
Plan SHA256 `50fd3b9779818d57cfee837f208f24e6d91be513254504dd6ca7151e64e49b52`.
Actual production requires fresh CPU/CUDA preflights after final curation.

Moved engineering training/reporting proof details to the linked
[validation page](../docs/quality-training-validation.md), keeping the main
[quality plan](../docs/quality-first-training.md) focused on data and comparisons.
Ruff check/format pass for both changed scripts. No model mathematics, quality
criteria or speed policy changed.

At13:15 PDT, the same original V43 source-scoring worker and handoff supervisor
are confirmed live; progress was35,840/88,508 sources and8,960 actual forwards.
RAM available82.83 GiB, root free86.52 GiB, SSD free504.65 GiB. Its original
root64/external500 GiB floors remain unchanged. No restart, new GPU job or
production study launch occurred. Final ranking, final manifest freeze and
quality training/evaluation remain pending. V43 is still the reference.

