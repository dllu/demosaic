# Completed V63/V64 first4k review

The matched data comparison is fully reviewed: 40,170 vs66,934 Commons sources,
both original20k schedules frozen at4000. Photo sRGB means35.76802/35.78297;
expanded-control+.014953dB, source95%interval[-.000798,+.033204]. Known/unseen
measured-CFA deltas-.019893/-.012780dB have negative source intervals. Against
V60, both photo means improve about.1dB but include extra training/fresh AdamW.
Highly saturated bright hue bias improves vscontrol but stays worse than parent;
moderate bright colors still shift. Weak-carrier gain is mixed. Actual native
views show soft cords, foliage, truss/fence crossings and very similar data arms.
No promotion/automatic continuation; V43 remains working reference. This boundary
does not establish convergence or universally reject additional data.

All primary/statistics/hue/artifact owners exited successfully. Independent
checks cover62,830 primary cases/84 comparisons/21 witnesses;1,344 analytic cases/
2,256 summary scalars;4,704 hue predictions/28,224 Torch64 metric fields/864 group
scalars;64 selected CPU arrays/384 fields. Actual visual review covers52 new PNGs
and six verified identical old hue PNGs. Public report retains58 complete crop
receipts;20 representative native512x192 PNGs copied byte-for-byte, including two
exact-GT photo sources per model and all four GFX regions. Four full101.996MP
RGB16 TIFFs verify, with eight full-TIFF/native-preview ROI checks exact.
V63/V64 restoration37.311/35.910s and2.278GB peak allocation;10s unmet. Paired RGB,
GFX lowISO and RawNIND references accurately labeled. Protected-final unscored.

The separate joint RAW-head CUDA engineering fixture completed seven discarded
B16/native256/BF16 updates with archived411d source,93model/93EMA/91Adam finite,
exact portable/manual EMA, all64 clean field cases max5.96e-8 and nonzero
trunk/tail/head gradients. Peak allocation21.328GB. Independent CPU inspection
verifies savedstate/config/source/127archivefiles/11inputs/logs/predictions. No
quality or deterministic CUDA restart claim.

A new head-only CUDA fixture is running separately against frozen32a source,
production-shaped B16/native256, original1000 head-warmup budget/LR2e-4/warm50.
It must verify all91 existing model/EMA tensors unchanged, only two optimizer
states and head gradients before any production warmup. Source/data plans remain
separate from V63/V64. Initial launch incorrectly resolved the virtualenv Python
symlink to system Python and failed at importing torch before training; original
failed log/launch retained, corrected absolute venv invocation is running as
PID2128527 creation1792213600.91. No production V65 launch yet at this entry.

Public report: docs/long-commons-v63-v64-first4k-review.md and matching resultsJSON.
Warmup fixture: /mnt/external/demosaic/benchmarks/raw-kernel-warmup-CUDA-preflight-v1/.
Commons downloader3989576 remains running; no duplicate or HDD wake. All prior
immutable model source, manifests, standing GFX selection and reviewJSONs retained.
