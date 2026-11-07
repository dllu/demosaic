# V170 released learned RAW matching comparison

Recorded: 2026-11-07T14: 11: 16-08: 00 (America/Los_Angeles).

The released April 2026 NLFeMF model was tested on the fixed 822 cached cases,
using one RAW-network call per case and two fixed RGB reconstructions. This
tests external pretrained weights; it does not isolate architecture or match
the project's freely licensed training pipeline. No training media were fetched.

Against V169 EMA, native 512 coarse-flat RMS falls 15.79–19.38% and quiet spatial
RMS falls 6.26–32.71%. These gains have substantial costs: mesh response falls
to 2.406–2.533% of exact constructed amplitude, quiet total/DC error rises, and
ISO6400 native-flat total RMS rises 17.67–19.03%. ISO12800 total-flat RMS improves
1.71–3.30%. All 72 ADC control inputs worsen in full RMS at both returns, with
fine periodic colored texture visible in the native gray/plane/bark/fur controls.
The nominal cab prior erases much of the green fence; the alternate prior is
speckly and still lacks crossings. Main sky is smooth at ordinary display,
but coarse fence is rougher and natural textures weaker. The DINO-parent
interpolation residual reduces some direct-Malvar edge fringes without fixing
the tradeoff. Keep V120 as general choice and the earlier useful prototypes.

All 60 fixed native figures were actually viewed in 15 original-detail sheets,
including both protected GFX scenes, both cab priors/windows and both JPEGs.
ISO100/AHD/JPEG references remain qualitative and unscored, never exact GT.
No source/noise, parent/DINO, training or original/dataz reads occurred.

Actual work: 822 unique quality roots and 4110 nested sampling calls, producing
1644 streamed RGB metric rows. Admission separately used2 CPU and 1 synthetic
CUDA full-model calls plus 4 CUDA sampler-only fixtures. Total new CUDA model
calls: 823. Both recorded workers are terminal. No scientific forward repeated.
Peak quality CUDA allocation: 2.420598 GiB. The mixed-size wrapper intervals are
not a whole-pipeline or100 MP benchmark.

All 13 CPU tests pass. Seven original class ASTs, all 141 weight tensors and the
pinned sampling kernels are verified; full original/ported CPU outputs match
exactly, with CUDA parity maximum2.24e-8 normalized. All 91 prior neural sources
remain unchanged. The public fetcher uses restricted weights-only extraction
with inert unused metadata and retains upstream MIT/Caffe notices.

All 822 event/input/parent bindings and 3288 input fingerprints are audited.
Independent posthoc metrics and NumPy64 RAW-to-RGB reconstruction cover only
the 36 preselected native cases: 72 RGB and 36 RAW arrays, 250,951,168 bytes.
The maximum independent RGB reconstruction discrepancy is 0.012779 DN16.
Other outputs have streamed metrics/fingerprints and in-process norm checks;
there is no complete new-array archive or all 822 posthoc array audit.
Independent Decimal arithmetic checks613 means.

Original preparation and initialization failures remain byte-preserved.
The shape projection originally assumed optional metadata; correction reads
NPY headers. The first worker missed a frozen import helper before any claim
or neural call. A separate prelaunch dependency receipt binds the added
unmodified helper, with unchanged inference AST and original frozen files.
The original plan was not edited. New52/114 GiB local/external reserves were
declared before this bounded trial; older guards and receipts remain unchanged.

[Completed report and native gallery](../docs/nonlocal-raw-comparison.md) ·
[Final evidence](../docs/results/v170-nonlocal-raw-final-v2.json) ·
[Publication checks](../docs/results/v170-nonlocal-raw-publication-verification-v2.json).

The fine-crossing/no-fabricated-structure goal remains open. A next matching
experiment needs matched free-image training and explicit low-noise identity
controls; the released checkpoint is useful as a measured comparison, not a
new baseline. Historical prep remains in the earlier diary entry and receipts.
