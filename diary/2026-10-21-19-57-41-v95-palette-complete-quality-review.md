# Palette follow-up stopped after complete quality review

Recorded: 2026-10-21T19:57:41-07:00 (America/Los_Angeles).

Completed the remaining color and GFX stages and actually viewed all remaining
native boards. All seven main workers/controller exited; all 96 saved triplets
are represented in 132 native display cells across 18 preselected groups.
The [complete review receipt](../docs/results/v95-palette-complete-quality-review-v1.json)
binds 17,824 actual joint/DINO forwards, checkpoint/input witnesses, primary
statistics, scalar/array audits and actual viewing receipts. Stop V96/V97 at
the declared final4k endpoints; neither is promoted or extended. V43 remains
the working reference and speed work remains deferred.

The brighter 2%/16px noisy carrier gain falls from V95's .61471 to .52083/.57749
in V96/V97. Noiseless four-pixel improvement is largely retained; the dark
10%/8px noisy carrier remains nearly erased. Independent math.fsum/std/min/max
checks cover 2,240 scalar cases and 3,760 summary fields, max error2.22e-16.
Shared V43/V95 learned analytic metrics are not bitwise equal to the older run:
all 3,008 fields per model differ, max scalar difference1.25e-6/2.21e-6. Malvar's
3,008 fields remain exact. All differences are preserved. Six native restored
previews differ by at most one RGB8 code, at most two values per crop; shared
noisy/GT/settings are exact. The frozen evaluator enables cuDNN benchmarking,
but selected kernels were not logged; no cause or DN16 bound is established.

The color-grid Torch64 array audit checks all 4,704 predictions/28,224 metric
fields, max error4.44e-16, plus exact native rerendering. The independent
scalar/percentile audit checks 864 descriptors, max3.47e-18. High-noise p95
channel bias is .005206/.041627/.008703 for V95/V96/V97; ADC p95 bias is
.002967/.030137/.028681. The wider palette mitigates the control's high-noise
bias but does not repair V95, and both continuations worsen ADC/tail behavior.
GFX's six regions show no convincing new endpoint advantage. LED variations
and the separate sharper ISO100 exposure are not exact GT. Published native
V96/V97 GFX files and sidecars are unchanged copies, including foliage/fence.

The queued lower-noise v1 controller correctly waited for all seven main
owners to exit, then failed while loading its first model: checkpoint tuple
defaults compared unequal with JSON lists. This is an operator bug, before
suite inference. A metadata-only CPU check established identical canonical
values; the comparison now accepts tuple/list serialization and still rejects
changed values/flags/keys and NaN. All21 focused tests pass.

Preserved v1 completely. A fresh bounded v2 kept all47 numerical source files,
checkpoints, data and protocols exact. It rendered all three four-source
panels, then failed its final image-only comparison because
build_native_crop_board.py was missing from the copied tool package. Actual
resource readings were healthy; neither failure was caused by a reserve stop.
Preserved v2's failed status/logs/outputs and did not repeat its inference.

Fixed future package closure and persistence of each condition's core checks
before optional image-only comparisons. An isolated, frozen CPU-only archive
now imports the helper and closes v2's saved outputs: 108 unique/finite rows,
independent summary arithmetic, exact metrics against the complete main panel,
and all12 repeated high-noise triplets pixel-exact. No postprocess controller,
worker, model construction or forward was launched. The recovery explicitly
distinguishes executed-prefix assertion/trace evidence from an independently
persisted per-condition runtime counter table, which v2 did not save. It does
not rewrite a failed runtime as a successful worker terminal.

Actually viewed all three secondary boards, 48 native cell placements/36
triplets. ADC/ISO100 fabric shows yellow/olive drift and lost fine cords even
when the input is nearly clean. This affects V43 already and worsens later.
RawNIND keeps fabric color closer in these cases while blurring lines; its
building geometry is softer. Retain this adverse evidence. The high-noise
repeat is a consistency check, not independent new quality evidence.
The [saved-panel review](../docs/results/v95-palette-native-photo-conditions-complete-review-v1.json)
binds all checks and actual views. Eight ADC triplets are published in their
own condition directory because saved basenames are reused across conditions;
the initial collision check fired before copying any file. Earlier outputs
and frozen preparation/launch receipts remain unchanged.

Updated the existing quality report, plan, requirements and experiment index.
Keep difficult development photos in evaluation and out of training. The next
quality work must address color/low-noise failures while retaining recovered
weak detail; simply adding training or widening the flat palette has not done
that. This is not SOTA, broad unknown-scene RawNIND superiority, new-endpoint
100MP qualification or ten-second evidence.

Final publication verification passes:90 static hashed references,20 newly
published byte-exact native triplets/sidecars and122 local Markdown links.
All four source/input guards pass (main1796 inputs/64 files, failed v1/v2 each
16/71, CPU archive16/72); all recorded runtime owners are actually absent.
No controller/worker claim exists for the CPU archive. Focused tests21,
Ruff and whitespace checks pass. No currently running model job is left by
this review.
