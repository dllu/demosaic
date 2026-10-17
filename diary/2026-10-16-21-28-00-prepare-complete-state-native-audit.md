# Prepare the remaining matched-data artifact audit

The preceding turn made progress: committed the complete v4 corpus review and
serialized score/hue operators. Revalidated actual owners 1988162 (trainer),
2036802 (primary) and 2055575 (statistics/hue), including creation times. V64 is
still training under the original 20k schedule. No owner was restarted, source
or manifest changed, or competing GPU inference launched. The full quality/speed
objective remains unresolved.

Implemented `scripts/audit_long_commons_artifacts.py`. Its entry point requires
completed/exited primary and trainer owners and their exact checkpoint/plan
identity. Both 4k whole states must match original 20k recipes, parent, seed,
source, validation protocol and four manifest hashes, with finite 91 model/91 EMA
tensors and 89 AdamW states, optimizer steps 4k and complete RNG. All 161 logged
domain/LR choices must match, and native/paired input hashes remain exact. Recipe
matching deliberately accounts for the resolved archived validation-protocol path
by checking the original guarded protocol hash.

The primary artifact audit expects 38 native PNG triplets, 26 F32 contexts and
four full RGB16 files. Correct F32 count is 8 shared GFX noisy/reference contexts
plus 18 three-camera contexts (three classical, two candidates, one RawNIND gain
mode for each of three cameras), not twice the single-candidate total. It verifies
complete file hashes, headers, finite values, source/ROI/noise/display metadata,
native160 panel rectangles, exact V60 noisy/reference pixels, and accurate non-GT
GFX/RawNIND labels. Two distinct exact synthetic-target photos and all four
standing GFX regions are required per arm.

Added an independent link from all eight GFX denoised PNG regions to their full
sRGB16 TIFF native coordinates. Because 65535=255×257, conversion to nearest
8-bit codes can be checked with integer arithmetic. All eight historical crops
match exactly. Both full camera-linear16 and ICC-tagged sRGB16 files must have
8746×11662×3 uint16 data and more than 256 sampled distinct codes.

Three-camera PNG panels are independently rerendered from their actual saved
F32 arrays, common WB/matrix/exposure and native ROI. An initial historical probe
found four single-channel/one-code differences among 12 restored panels. The
full replay's 36 noisy/restored/reference rerenders have six changed channel
values total, at most one per panel. Declare and retain a preview-only bound of
≤1 code and ≤16 changed channel values per 160×160 panel, before future V63/V64
outputs. This is not exact cross-device arithmetic, a metric/color tolerance,
or a relaxation of exact saved noisy/reference pixels. No rendering change or
output correction was made.

CPU preflight checks the actual finished V63 state plus genuine older V59/V60
native artifacts. The first attempt reached the final historical file witness
then failed because the test driver preferred relative `path` over
`absolute_path` for existing TIFF receipts. Corrected only the private driver and
used a fresh v2 directory; public checker source is unchanged. Both logs/frozen
sources remain. Recovery passes all selected 38 PNGs/26 F32/four RGB16 identities
against the existing complete audit, all eight full-TIFF crop links and 36 F32
rerenders. It rejects the actual pending primary workflow before any output.
No model inference, GPU initialization, RAW decode, V64 state or visual-review
claim follows from this engineering replay.

Queued tested CPU checking behind actual statistics/hue owner 2055575, creation
1792210364.08. New owner 2060575, creation1792211119.29; driver
`77d89774b96288633dcca30fe153940e3df0467aaf6ad01f4c94c32d0cc4d0c7`.
It archives all 82 public operators and guards the upstream sources/inputs. Uses
repository cwd for saved result registries and old c905 model package on
PYTHONPATH. Terminal status explicitly awaits actual native review and quality
decision. No automatic continuation, promotion or protected-final score.

Public CPU and queue receipts and the longer-data-stage documentation are updated.
After actual primary/statistics/hue/state-native completion, inspect the native
outputs and interpret the matched comparison before deciding further training.
The default-off RAW reconstruction candidate still needs actual CUDA/B16/native256
gradient, memory, state and portable-EMA evidence before any production trial.
