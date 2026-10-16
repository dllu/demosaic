# Callable recent RAW reference and standing GFX CPU review

The previous goal turn made concrete progress:96 color-flat predictions were
independently audited, genuine recent RAW weights/source were acquired and
strictly checked, actual native CPU and sm121 build checks completed, and two
photographic cascade outputs/native crops were reviewed and pushed as e70dad1.

Revalidated actual owners601329(V58),580845(new4x) and3989567(downloader).
V58 continued past5000 on its original schedule and all other jobs stayed live.
No GPU inference/compute or source hard-drive access was added.

Added an optional pinned Nonlocal Match-Filter reference to photographic,
paired, analytic and GFX evaluators. The actual PatchMatch import dependency
also compiles without CUDA execution, so the callable needs no import shims or
numerical substitutes. Hashes, source revisions, weights, physical normalization,
RGBG packing, input-only std maps and original clipping rules are retained.
Native network calls stayB1; an outer mixed-CFA batch matches serial exactly.
The source launches CUDA sampling on stream0, so nondefault caller streams are
explicitly rejected. Actual default-stream CUDA numerics remain pending.

The full CPU suite passes500 tests/8CUDA skips in128.29s. The added stream guard
then passes12 targeted CPU contracts/1CUDA skip. Genuine callable outputs match
both earlier full256px CPU predictions bit exactly, including a final recheck
with the stream restriction present. The optional evaluator preflight completes
224 synthetic records(2sources,7conditions,4CFAs,4methods) and8 records from2
selected real-development crops. These are mechanical checks,not broad scores.

All four fixed512px GFX contexts complete on CPU. Their noisy and independent
ISO100 panels match the parent bytes; all6 new native images were viewed.
Foliage/fence direct rows compare V43/newreference/RawNIND-CFA-channel without
calling any restored output GT. The new fence retains more grain/less regular
wires than V43; RawNIND's mesh is more blurred. Fine truss/leaves remain soft.
This one scene supplies no broad winner,full102MP result or model promotion.
Four float contexts/18 rendered panels verify; all3 preflight PNGs were viewed.
Sources/ROI/checkpoint/noise/exposure and exact source snapshots are retained.

Details:docs/nonlocal-reference-integration.md. The mature V58 review,new4x
completion,CUDA reference checks,broad real superiority/protected-final scores
and10-second speed gate remain open. V43 README crops stay fixed.
