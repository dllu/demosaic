# Independent full-quality metric audit queued

Recorded: 2026-10-24T00:26:57-07:00 (America/Los_Angeles).

The previous turn made progress: public evaluation operators now support the
eight-view policy and the complete frozen comparison is queued. Rechecked all
seven exact original handles live; V112 continues training. The full objective
remains open, including substantial real-photo improvement over the strongest
tested RawNIND release and the 100MP runtime target.

Implemented an independent retained-prediction audit for all five queued
panels. It reconstructs input fingerprints, rehashes saved means and computes
NumPy64 photographic PSNR/chroma/gradient, measured-camera CFA error/count,
carrier/flat response and analytic color/phase errors. Source-weighted V104
contrasts and scene comparisons against the stronger RawNIND pre-upsampled
reference reuse original controls. Module forwards raise an error, so this
audit cannot silently run neural inference. Original photo regeneration needs
CUDA RNG after the evaluation owner exits; texture keeps its CPU draws.

Actual CPU engineering proof rescored two retained photo observations and one
camera crop. Maximum PSNR discrepancy is 0.00000312687dB; all input fingerprints
match. Separate metadata proof reproduces all 112 existing texture input
batches exactly, checks four saved V111 colors (including its worst ADC case),
and recovers the published V104 photo/known/unseen means through the new
source-weighted joins. Zero new neural forwards and no CUDA initialization.
These are verification results using existing artifacts, not new quality gains.

Executed audit v1 and its plan/proofs remain intact. Audit v2 tightens
non-PSNR bounds to at most 2e-6 and uses distinct output/design filenames;
observed CPU discrepancies already satisfy those bounds. Numerical operators
and prediction joins are unchanged.

Audit controller 4138085, creation time 1792826759.29, waits for exact full
evaluation controller 4127938 to exit successfully. It then runs the complete
score audit; completion still leaves native-image review pending. Future CUDA
training must wait for this audit owner too. All eight recorded handles were
verified live. Existing training, evaluation, exports, material queues and
current V104 selector remain unchanged.

[Current status and scope](../docs/dihedral-quality.md#full-comparison-queued) ·
[Audit design, CPU/metadata proof and launch evidence](../docs/results/v104-dihedral8-audit-queued-v1.json).

