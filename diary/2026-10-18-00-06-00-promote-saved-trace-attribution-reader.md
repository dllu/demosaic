# Promote and verify the saved-trace reader while training continues

Previous goal turn made progress by preparing and queuing actual FP32 GPU
profiles behind complete quality evaluation. Revalidated live training
controller2645898/1792305192.32 and child2645905/1792305192.6, quality
controller2667688/1792305841.61 and profile controller2714232/1792306477.92.
No restart or inference overlap. The first arm progressed beyond3250/52000
to3575/57200 optimizer/example draws during the work below.

Promoted the already-owned private Kineto reader into
`scripts/summarize_inference_trace.py`. Preserve External-ID CPU association
and the independent runtime-correlation join, adding runtime thread and whole
CPU-operator containment checks. An optional annotation prefix selects the
current demosaic ranges. Reject nonfinite/negative intervals and ambiguous CPU
IDs. `--require-cuda` requires positive device activity and complete matching
launch associations; a CPU trace cannot pass it. No Torch import or model
execution. Exclusive totals partition GPU activities once; nested inclusive
totals overlap and are not elapsed wall time.

Twenty-three focused tests pass in.03s, covering asynchronous host/device
timelines, partially overlapping ranges, other threads, zero IDs, incomplete
or conflicting associations, CPU-only input and invalid intervals. Ruff passes.
Replayed two real completed GPU traces:4155 V37 and1209 V67 activities. All
previous numeric attribution tables reproduce exactly, independent of keyed
table row ordering. Both added runtime checks pass all5364 activities. Decimal
duration sums agree within the declared1e−8us arithmetic bound. These are
historical models/precision policies, not current GPU performance evidence.

Current2k CPU traces yield13/15 ranges, one call each, and270 learned-branch
`aten::conv2d`/104`aten::layer_norm` calls per model. Physical core operations
and DINO ranges are excluded from these learned-branch counts. Both CPU traces
are rejected as GPU evidence. All input trace/report hashes remain unchanged.

Private executed source/driver/results are in
`/mnt/external/demosaic/benchmarks/mixed16-trace-reader-CPU-v1`.
Public registry is an exact byte copy of its result, SHA
`557d06d3fb94525c2fa86a0b196d0067144b9f72394533dafea5b29889328e21`.
The current profile documentation records the post-completion command and
interpretation. Existing frozen training/quality/profile sources are unchanged;
the queued GPU results and their analysis remain pending. No additional GPU
job, optimization, promotion or protected-final scoring. Goal stays active.
