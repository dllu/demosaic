# Audit fine-frequency coverage and prepare optional weak targets

Recorded: 2026-10-24T09:11:21-07:00 (America/Los_Angeles).

Previous goal turn made progress in `67c95d3`: optional band supervision,
actual V112 CPU/parameter checks, and repaired idle endpoint reviewers. It did
not establish a trained fine-detail gain. This turn investigates clean-source
coverage while the original V114/V115 budgets continue unchanged.

The frozen CPU audit measures 224 native256 clean targets at actual deterministic
source indices from V114's completed first 9,775 updates. It balances 32 each
of flat, weak-random, weak-fiber, strong-procedural and native-RAW targets,
plus 64 photos, of which 14 receive existing contrast attenuation. This is
source coverage, not a training-quota or population estimate. It reads cached
SSD arrays only, with no model/encoder/optimizer, new noise, RAW decode or CUDA.
Global Python/Torch RNG remains unchanged; source/ROI/generator/target hashes
and all 224 arrays are retained.

The .225–.35 cycles/final-pixel median relative luminance RMS is .12580 for
photos, .02219 for attenuated photos, .11866 for native references and .05175
for strong procedural targets. Legacy weak random/fiber sources have only
3.54e-7/1.68e-7. Their nominal random support ends below .22, and fiber
fundamentals span 6–32 pixels. Thus dedicated weak targets have a frequency
gap, while sampled natural and strong targets already contain fine energy.
Native descriptors include residual reference noise and are not exact GT.
Hann-windowed target spectra do not establish recoverability or useful detail.

Added optional fine-v1 frequencies: random support 1/6 to a sampled .34–.40
cycles/final pixel; fiber fundamental periods 3.5–6 pixels. Kind, local seed,
background, tint, peak contrast, shape RNG and downstream geometry draws stay
coupled. Targets remain continuous float32, generated before final area2.
The new fine_weak_texture_fraction defaults to zero and fits inside the existing
weak quota. A prospective .075 within weak .15 replaces half the weak draws,
or 3.75% of all examples under the current 25/25/50 domain mix. Photo/flat/
strong/native/paired allocations are unchanged. A selected fine draw loads no
photo or discarded strong target. Validation disables it; resume rejects a
changed quota. The argument is appended to preserve positional CleanDataset API.

Actual full-manifest reader proof makes 128 clean calls at the 64 audited weak
indices. All 64 new-default targets match frozen baseline arrays bit for bit.
Only 38 selected fine replacements change (18 random, 20 fiber); the other 26
remain exact, and all 64 post-generator Python RNG states match. No photo IO
occurs during weak generation. Matched replacement medians in the fine band
rise 3.28e-7→.00970 and 1.76e-7→.00584. No model outcome exists.

The pre-test reader-v1 plan was never executed and is preserved. Reader-v2
contains the actual source/log/results. Public constructor argument ordering
was subsequently made backward compatible; all executed/current function
bodies remain AST-identical. The frozen original sources remain intact.
The public audit helper now also forwards an explicitly configured fine quota;
the completed legacy audit is not rerun. Its original import-order snapshot is
preserved with its executed hash.

28 targeted tests pass in 2.59s, including real tiny-model interrupted/resumed
training with bit-exact model/EMA/Adam/RNG. Unit-fixture setup first needed the
scripts import path, camera-conditioning flag and proper bin4 metadata; the
corrected final test source is separately retained. These are engineering
iterations, not repeated scientific results. Ruff passes for all six public
Python files. No new production/GPU job or training recipe is introduced.

Published a frequency chart and two native160 clean-target pairs, with identical
ROI [48,48,160,160], exposure1 and linear-sRGB→sRGB display without resizing or
contrast stretching. Actually viewed the chart and both pairs. These are
generated clean targets, not noisy/restored/GT performance comparisons. Their
selection uses generator level×peak contrast for visibility, with no model
outcome. The 224-source and 64-index results, arrays, recipes, pixel hashes and
publication source are bound in the public receipt.

Updated source/research/current-quality docs to distinguish the active legacy
weak profile from the disabled new profile. Corrected incoming-corpus docs:
V112 evaluation is complete; V114/V115 use the current 90,864-source cohort.
The seed62 V109/V110 prospective exposure counts remain explicitly unlaunched
history, not current-production receipts. V112 stays selected. Quality testing
of the new profile awaits a later matched training comparison after the active
architecture study; normalized band supervision also remains off.

[Coverage, native pairs and limitations](../docs/fine-weak-texture-coverage.md) ·
[Public source/reader receipt](../docs/results/fine-weak-frequency-coverage-v1.json).
Private evidence: .cache/current-quality-20261023-v1/training-frequency-coverage-v1/
and fine-weak-texture-reader-v2/. Originals and GFX holdouts remain untouched.
The linear-DNG/hot-pixel branch tip 4381fc23 remains an ancestor of HEAD.
Broad real-photo superiority, fine-detail recovery and 100MP/10s remain open.

Final publication verification at 09:14 PDT passes 25 frozen plan guards,
1,437 distinct bound files, all four native display-cell reconstructions and
180 local doc links. The first bookkeeping verifier incorrectly assumed an
empty list for queued completions; both owners actually use empty dictionaries.
Its failure/source remain preserved, and corrected verification-v2 passes
without repeating scientific work. Training 867877/1792848017.25 is live with
V114 at logged step 11,850; evaluator 986158/1792855221.87 and independent audit
986159/1792855223.35 remain live/waiting with no children or completed stages.
Current V112 selector and checkpoint hash are verified. The 28 tests are not
rerun for publication; final source hashes are retained separately.
