# Native crops and cached GFX test

Recorded the user's standing requirement: improved-model performance reports
include at least two small noisy/denoised/GT crop triplets at 100%, and keep a
representative set in the README. Added this to AGENTS.md and the evaluation
documentation. Synthetic and paired-RAW suites now automatically write native
160-pixel triplets, pixel/coordinate receipts and a Markdown report. All methods
share preselected input regions and display transforms. Real RGB references are
explicitly auxiliary or qualitative rather than exact GT.

Cached the specified ISO6400 DSCF3842 and ISO100 DSCF3883 locally (230 MiB) with
SHA-256 receipts. Originals were read only; subsequent decoding used the cache.
EXIF confirms GFX100S/55 mm, f/1.7 1/300 s versus f/5.6 2.5 s. Both have
11662×8746 visible pixels. Their different framing/time/aperture/motion makes
pixelwise scoring inappropriate. This scene/siblings remain evaluation-only.

Added scripts/report_raw_pair.py and fixed native sky/building selections. Shared
WB/matrix/+2 EV display exposure; the independent ISO100 AHD reference is
calibrated to its own CFA units. A narrow intensity range makes the input Haar
shot/read fit unidentifiable, so conditioning is explicitly a nominal ISO prior.
Local source/weight snapshots, complete settings, and cropped PNGs are retained.
README examples use two fixed synthetic observations with exact GT; real GFX
crops and their caveats are in docs/gfx-qualitative.md. Commons crop attributions
and CC BY-SA 4.0 notices accompany the README and receipts.

Validation: pixel-for-pixel test verifies no interpolation/resizing in the PNG
panels; a CPU suite smoke test verifies report embedding and frozen weight hash.
Actual CUDA synthetic and paired-RAW reports and the GFX comparison were rendered
and visually inspected. Full suite: 155 tests passed; Ruff clean. The new flat-only
refiner is separately reviewed and rejected for photographic quality; V11 remains
the illustrative checkpoint. Overall real RAW quality goal is still unmet.
