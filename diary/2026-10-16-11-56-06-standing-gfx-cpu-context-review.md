# Standing GFX scene checked on CPU while long GPU training continues

Previous turn was progress: bcc7be5 added actual CPU comparisons on three cached
additional cameras and two fixed exact-GT source examples. Rechecked the live
original controller/trainer, current source, memory and cached GFX pair before
continuing. The broad quality/SOTA/speed objective is not yet established.

Extended the existing paired-capture report helper with explicit CPU FP32 device
selection and float-array persistence. GPU remains its default. Reject CPU half
neural/refinement labels before any input/output access; both guard cases were
actually exercised. Only report code changed; production package and running
frozen evaluation/source hashes remain unchanged. Ruff passes.

Actually reran retained V43 and the completed fresh no-context 10,000 checkpoint,
plus both RawNIND gain variants, on four native 512px contexts from the local
DSCF3879/3880 caches. All source hashes match the standing cache receipt. No
original photo directories were accessed. Input-only shot/read remain
.0014635775921166604 /1.0715704128646712e-6 and display remains ×4/+2 EV with
shared noisy WB/matrix. The ISO100 f/5.6, 3s frame is an independently AHD/
own-CFA-calibrated qualitative reference, not exact GT; no reference scores.

All 16 primary triplets and four direct learned comparisons were visually
inspected and verified. All 24 float arrays pass hash/shape/dtype/finite checks:
four noisy packed contexts, four reference crops and 16 restored RGB contexts.
Every primary panel rerenders byte-exactly. Noisy/reference panels match across
methods, and direct panels copy parent pixels without resampling. Runtime
records no CUDA context; full-frame CPU mode was not executed. Four exact-GT
triplets for these same checkpoints are reused unchanged from the preceding CPU
review, rather than recomputing their inference.

Both learned methods retain more continuous fence lines than RawNIND. Fine leaf
and building detail remains soft, with no clear new winner over V43. Aperture,
motion, depth and lighting differences in the ISO100 capture prevent assigning
all reference differences to restoration. A full 512px sky input-consistency check
finds at most 0.5675% learned-model phase-mean change relative to noisy CFA means.
It uses no ISO100 pixels, supplies no noise-confidence bound, is not a quality
score and is not used for model selection or display adjustment.

[Review](../docs/gfx-none10k-cpu-context-review.md),
[full receipt](../docs/results/gfx-none10k-cpu-context-review.json).
The main GFX page now correctly identifies V43 as the current README reference
and distinguishes these context outputs from historical full-frame galleries.
Keep that reference. Original S/B training and full matched numerical/analytic/
102 MP GFX review remain pending; no new full-frame output, speed claim, model
promotion or final-holdout scoring occurred in this turn.
