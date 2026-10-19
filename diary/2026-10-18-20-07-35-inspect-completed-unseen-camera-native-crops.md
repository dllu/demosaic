# Inspect the completed unseen-camera native crops

Previous goal turn was progress: all six completed known-camera triplets were
actually viewed and their partial notes committed. Revalidated the same live
full-photo reviewer and worker, plus all queued followers. The full suite is
still running, most recently38,851 of74,424 saved records. No duplicate job,
new own GPU work, training change or early quality selection was introduced.

Actually viewed all six completed unseen-stage triplets at original resolution:
LucieB_3apples and LucieB_Coulicoco for V80 control, V81 bank context and genuine
V63. The original512×192 PNGs contain unresized160×160 panels. Hashes, metadata,
prepared manifest and both actual cached source NPZs match. Across the three
methods, source/ROI, noise estimate, display exposure, variance multiplier, WB
and color matrix match. Noisy and auxiliary reference panels match pixelwise.
No resampling, re-encoding, enlargement or new inference was used for viewing.

In3apples, all three strongly reduce colored speckle on the mostly smooth dark
brown region while retaining broad tonal variation. The outputs look close at
the fixed native display. InCoulicoco, all three retain broad diagonal/curved
warm-colored boundaries and some faint central marks while strongly cleaning
color noise. Their preview appearance is again close. The auxiliary references
retain finer grain/pattern, without identifying from these views which part is
true detail versus residual noise or demosaicing. These smooth/broad regions
give limited evidence about thin-detail recovery. No clear bank-specific gain
or new failure is visible in the two fixed ROIs; no wider conclusion follows.

Saved the partial record manual-review-unseen-fresh-v1.json at the review root.
It contains the source/checkpoint/ROI/conditioning/display hashes, absolute
prepared-crop paths, actual-view observations and matching-pixel checks.
manual_review_completed remains false and quality_decision remains null. The
combined known/unseen partial review now covers12 triplets/36 displayed panels,
not every final comparison board or cell. The real AHD references are independent
auxiliary RGB, not exact GT; measured-CFA scores remain primary.

Full numerical review and all final V43/RawNIND, synthetic exact-GT, GFX foliage/
fence/sky/building/lights, carrier/flat, hue and highlight comparisons remain
required. These partial real-camera views do not replace the required exact-GT
report triplets. No source photo, fixed criterion, README image or model default
changed. The global quality/speed goal remains active and incomplete.

All54 immutable file bindings, the12 distinct viewed images/four source groups,
native panel geometry, method/display/source checks and diff checks pass. The
reviewer, full427 worker and all queued followers remained live; the full suite
had40,473 saved records at the final verification. No model source changed or
unrelated test suite was rerun for these view notes.
