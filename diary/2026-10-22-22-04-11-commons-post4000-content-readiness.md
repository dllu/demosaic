# Reuse complete Commons content references and queue new-source overlap review

Recorded: 2026-10-22T22:04:11-07:00 (America/Los_Angeles).

Built the complete10287-source reference bank from existing9855 vectors plus432 prior-arrival holdout vectors. Pools:10092 Commons heldout,150 native and45 protected. All10087 current corpus heldout IDs and five additionally protected prior holdout hashes remain represented. Every selected cached image passed whole SHA/header checks; independent uint32 comparison verifies every output vector bit-for-bit against its bound source. Both original8-image CPU encoder replays are bit-exact. Official DINO and Torch RNG remain unchanged; no CUDA or restoration/quality inference. Bank runtime30.29s, with no fresh full-bank encoding. Preprocessing source/color bytes match the earlier query.

The unlaunched v1 plan exposed a prospective path assumption: three protected arrays reside in the original workspace SSD cache. Fixed the helper to bind that cache root explicitly for an archived worker; v1 is preserved as superseded before any encoding. Corrected v2 passes actual population/mapping validation from the frozen import path and completes all checks. Thirty bank/extension tests plus seven retrieval tests pass; Ruff/format checks pass. Explicit288GiB budget retains the548GiB default and48GiB RAM guard.

Preliminary title matching on all3809 selected arrivals has3418 train-bucket queries against10092 prior plus391 new heldout anchors. It flags972 title risks and11 uninformative titles;2435 have no title flag. These are not eligibility/source-quality decisions; the actual final candidate population requires IDF recomputation. No new source has been admitted.

Ran the genuine two-query retrieval fixture with the new budget. Every feature byte, all10 saved neighbors and contact PNG exactly match the earlier fixture. Viewed all7 source pairs/14 thumbnail cells. All52 production sources match this actual fixture. The new query queue is live behind the exact preparer and complete cache/area/protected receipt; it will compare new sources against the full bank and new reserved hashes. Originals, current training/evaluation membership and fixed V102/V103 plans remain unchanged.

Bank:`/mnt/external/demosaic/commons-post4000-content-bank-20261022-v2/`. Query:`/mnt/external/demosaic/commons-post4000-content-retrieval-20261022-v1/`. [Complete evidence](../docs/results/commons-post4000-content-readiness-v1.json).
