# Prepare the remaining selected-color native review input

Previous goal turn was a verified45s wait on full427 child
3079810/1792324105.58. Revalidated the same live owner. Full-photo records
advanced from15,208,393 to18,516,001 bytes during this CPU work; no final
summary yet. The full matched quality/visual decision remains pending.

Inspected the completed earlier selected-color report and native helper.
Its original eight crops and eight extra audit crops share the existing hue
analytic schema and identical recorded model labels/checkpoint hashes. The
extra collection is named additional_native_crops rather than native_crops.
No board reader change is required. Prepared a small private adapter that
accepts a completed report/audit pair, copies only the eight extra PNGs and
wraps that named collection. Every crop metadata entry stays unchanged.

Executed the adapter on the completed first32k selected-color outputs.
The pinned, tested native reader accepts the original report and wrapped
audit, verifies shared source/ROI/noise/display/GT and checkpoint identities,
and renders all16 triplets as24 unique native160px cells. Independent
readback compares all48 original noisy/restored/GT panel blocks to their
board positions exactly. All18 report/audit/PNG source files and all extra
crop metadata remain unchanged. Torch is never imported. No new prediction,
score, manual visual review claim or model quality finding.

Private adapter and preflight evidence:
/mnt/external/demosaic/benchmarks/native-selected-color-bridge-CPU-v1/bridge.py
and preflight/. Adapter Ruff passes. The root board reader and every frozen
workflow remain unchanged. Public exact audit copy SHA
b78b9b569afb3969beb6fd89b0be8aaed4bc23958a2626831d3bccec78f5bb68.
The bridge receipt SHA is
9efadb40e635e08c3901501788d5a1428eb85a9ffdb6d263cb9ba926b34766a7.

When the new10k selected-color report/audit are complete, run the same adapter
with --source /mnt/external/demosaic/evaluation/packed-isotropic-mixed16-quarter-colored-CPU-v1
and a new --output under benchmarks/mixed16-quarter-native-review-v1/.
Inspect the resulting native board then; this replay is earlier-model format
evidence only. Continue the current full427/analytic/GFX/camera/color review
and the exact final-summary match for the already inspected photo candidates.
