# Matched fresh no-context/S10k on three additional cameras

Previous turn made progress: independent statistics audit 7a44328 was committed
and pushed. This turn confirmed controller 164667, B trainer 300610 and downloader
3989567 actual identities/liveness; B started this turn at 4,825 with finite loss.
No GPU job or training policy was changed.

Ran three new CPU FP32 S10k context forwards on the fixed Q2, a7R II and GFX50R
selections. Recovered the noisy packed CFA directly from the prior retained
unquantized bilinear RGB, whose observed sites preserve measurements exactly.
Complete bilinear and Malvar float roundtrips match prior arrays bit-exactly
for all three cameras. No original/cached RAW was read; no no-context or
RawNIND inference was repeated. Source/ROI/noise/WB/matrix/exposure are unchanged.
S uses the prior immutable 10k EMA snapshot ae74bc… and matched 403-input receipt;
candidate/baseline snapshots and source package hashes are verified.

Execution `/evaluation/three-camera-fresh-none-S10k-cached-cpu-v1` completed:
12 S/RawNIND global-or-channel primary triplets, six none/S direct rows, three
packed input arrays and three restored RGB float contexts. Actual independent
artifact audit verifies all 18 PNGs/six arrays, byte-exact primary-panel
rerenders, shared noisy/RawNIND panels, direct copied pixels and metadata.
All 18 new PNGs were actually viewed in batches before publication.

Q2 shadows and Sony window/fuselage detail remain soft; none and S look close.
Both retain sharper GF50R concrete seams/more surface variation than RawNIND,
but variation is not proven true detail without a clean reference. No new S
benefit or promotion established. RawNIND is labeled comparator, never GT.
Two existing S exact-GT triplets are reused unchanged in the same report.
Published 18 native images and provenance as a supplementary section in the
existing matched S/no-context review. README/V43 and training membership remain.

Initial scratch schema guards stopped before output because the old report uses
`neural_precision` and enriches its selection records. Corrected field/subset
checks then completed. Initial successful artifact audit had an unused import;
the final v2 audit removes it, passes Ruff and reruns successfully without model
inference. Both executed versions remain archived with hashes. Final replay, audit and publication drivers pass Ruff. No CUDA context initialized. Production
package/live frozen training and evaluation files are unchanged; the existing
production validation remains applicable. B/full-suite/analytic/full-frame
quality review remains pending.

Final check: B reached step5,600 with finite loss. Controller/trainer/download
process creation identities and frozen package/evaluation hashes remain intact.
