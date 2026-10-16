# Inspect target consistency before expanding supervision

Added a read-only measured-CFA training/quarantine diagnostic. Same-color
observed/reference residuals use declared noise scaling and lag2 correlation;
a weighted gradient fit is a rough subpixel-translation descriptor. No model,
target interpolation, correction or automatic rejection is involved. Guarded
against held-out split use and changed source/crop bytes. Nine targeted tests
recover known fractional offsets for allCFAs, distinguish white noise and a
blur-only mismatch, and check invalid/masked inputs and split restrictions.

Actual train32:64 pairs/576 crops,61 with direct same-color support; case-median
lag correlation median.01223. Three have no direct CFA intersection after an
odd shift, so no interpolated surrogate score is fabricated. Selected low-ISO
Kortlek/wetwood cases have.23387/.19400 correlation and first-order descriptors
around.3–.4 sensor pixels. Pilot2:four pairs/36 crops, three supported; Bark1600
shows.20756 and[−.345,−.292], while the bouquet is near.01. Reference noise,
correlated sensor noise, gain/black offsets, defocus or motion can explain
structure; these are inspection priorities, not proven geometric corrections.

Published native160px noisy/AHD-reference data pairs, precise provenance and
two actual-run receipts. AHD is not exact RGB GT and these are not model-output
comparisons. Most pairs look consistent by this descriptor; no claim the whole
training set is broken. No dataset/target/recipe change follows yet.

The matched fresh three-arm workflow has completed3000 updates and is scoring
full427 before its GFX review. ADC-policy GPU validation still waits for its
actual exit. CPU preparation of the52 screen-clear scene candidates continues
separately. The goal remains active; no promotion or completion claim.
