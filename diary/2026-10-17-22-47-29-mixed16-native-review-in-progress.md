# Native review advances while full GFX comparisons run

Previous goal turn made progress: genuine2k-parent CPU restart preflight,
production-loop integration tests, independent source/counter audit and first
full427 native inspection are complete and pushed inba8f312. The full
photographic inference and analytic producers have exited successfully.

At this turn's start and throughout, controller2362748/1792295060.93 and
full-GFX child2517437/1792301749.85 are verified live with their exact creation
handles. The child is the sole observed CUDA compute process and consumes GPU
work. Its first candidate exports appear as it advances through the models;
there is no evidence of a stopped job and no restart or signal was sent.
This is progress plus a verified wait, not a blocker or project completion.

Completed two native comparison boards from final known/unseen and analytic
summaries. They cover all32 camera triplets (eight methods × four selected
cases) and12 analytic triplets (four models × three generated cases). Every
source PNG hash, shared source/ROI/noise/display metadata, and shared noisy/
reference panel matches. All58 copied160×160 cells are exact after PNG reload,
without resizing. Both boards were actually viewed at original resolution.
Camera AHD is an auxiliary independently demosaiced reference, not exact GT;
analytic clean targets are exact generated GT.

Also inspected the eight already closed full-frame GFX candidate triplets:
V72/V73 × sky/building/foliage/fence. They come from the blended complete
102MP CUDA FP32 outputs, rather than the earlier CPU512-context previews.
All16 board cells are exact native copies. Across candidates, coordinates,
conditioning, display exposure, WB/matrix and outer panels match. The board
was actually viewed at original scale. DSCF3880 remains a separate ISO100/f5.6
reference, not GT, and the scene/siblings stay outside training. Final report
matching and RGB16 integrity checks remain pending with the producing workflow.

Private assembly receipts and explicit manual-view records are under
`/mnt/external/demosaic/benchmarks/mixed16-native-review-v1/`.
The three executed assembly scripts/outputs are separate immutable provenance;
none changes inference code or source artifacts. Ruff passes for both new
assembly scripts. Board SHA256s:

- Cameras:7d7610d7c729edea5fc032625fb68cd86e775499cc7a8c06a7cbb92da804e0c4
- Analytic:916c8434200ea302e0a7b1fbf3494302cf4aab22aa50b0a603964f949bcee372
- Candidate full GFX:246503897a2078ac5f5dc42950b385ae8a085820eb9938fbd00a3b710462c7ba

This turn covers52 native triplets, with74 exact board cells. Findings stay in
their view records for the forthcoming complete performance report; no partial
panel is published as that report. The earlier complete full427 board covers
another16 triplets, with its final-summary match already verified.

At the latest recorded poll, the GFX child has been live700s and has produced
six TIFFs/twelve crop PNGs; the full report is not yet published. SSD514.51GiB
free. The downloader remains stopped, leaving export headroom. Full comparator,
three-camera, selected-color, statistics, hue, artifact and sensitivity work
continue under the frozen plan. No training extension, inference precision
change, model promotion or protected-final scoring. The full PROMPT.md quality/
speed objective remains active and unmet/unproven.
