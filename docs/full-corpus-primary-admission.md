# Full-corpus endpoint benchmark admission

**The local-model CPU benchmark has passed its real three-case qualification.**
Fresh V120 outputs and every metric row are bit-exact to the existing closed
CPU controls on a photo batch, known-camera batch and unseen-camera batch.
The20k endpoint's native review and complete benchmark are queued behind the
existing trainer's successful phase completion. These are waiting jobs, not
completed primary scores. V120 remains the recommendation.

[Qualification, frozen sources and bound job observations](results/full-corpus-execution-followup-v1/publication.json) ·
[Three-case result](results/full-corpus-execution-followup-v1/primary-preflight.json) ·
[Independent NumPy qualification](results/full-corpus-execution-followup-v1/primary-preflight-independent-audit.json).

The qualification uses the immutable10k EMA as the candidate solely to exercise
the complete path before20k exists. Six actual CPU root calls reuse three
checked frozen DINO computations. Runtime196.503s excludes model loading and is
not an isolated speed benchmark. Both models' full weights and CPU RNG remain
unchanged, with no GPU/RAW decode/new corruption/optimizer calls.

## Exact scope and numerical policy

[collect_local_primary.py](../scripts/collect_local_primary.py) consumes the
already-exported canonical tensors from the [scene-primary admission](whole-scene-context-primary-admission.md).
It removes the unused whole-scene encoder for these local models and preserves
the local DINO path. CPU IEEE FP32, contiguous B4 and four threads match the
existing CPU controls. All neural source files match that qualified path; only
the unimported training checkpoint-IO source differed when the snapshot was made.

Full coverage requires **3,162 canonical batches**:

| Panel | Batches | RGB observations |
| --- | ---: | ---: |
| 427 photos +16 separately labeled synthetic sources,7 conditions/4 CFAs | 3,108 | 12,404 |
| Known:4 scenes/8 captures | 24 | 72 |
| Unseen:5 scenes/10 captures | 30 | 90 |

The collector checks actual packed/variance/CFA/WB/matrix fingerprints before
and after every batch. Each loaded EMA tensor and frozen DINO hash is checked;
local encoder requests are replayed only after exact input/weight/config checks.
Targets are passed only to metrics. No complete-scene noise, original sensor
decode or new observation is needed for this local-model benchmark.

Borders remain8 pixels for photos and32 for camera crops. Metric formulas and
source/scene/pair/CFA aggregation are unchanged. The host's reference CPU SSIM
convolution avoids the known oneDNN JIT failure. Camera AHD RGB remains auxiliary,
independently demosaiced reference data, not exact GT; measured-CFA scores are
computed with the original masks and sample counts.

The independent NumPy qualification covers24 model/crop rows. Maximum PSNR
error is4.47e-6 dB and chroma/gradient differences are below1.5e-9, within the
**unchanged**5e-4 dB/2e-6 legacy tolerances. SSIM/additional masked metrics retain
the collector's original implementation. A native prediction-archive adapter
also passes the established path/hash/logical-value reader on its two photo
model/batch records, using exact same-filesystem hardlinks rather than copying
or changing tensor pixels. Neither qualification is a full427 evaluation.

## Queued endpoint and subsequent evidence

The exact owned review queue waits for the existing v7 control stage's successful
return code, completed20k horizon and immutable endpoint. It independently checks
91 raw/91 EMA tensors,89 finite Adam states all at20k, RNG and original horizon;
the checkpoint must match the retained20k receipt. It does not restart training,
change data/optimizer/schedule or interrupt the99k long-arm continuation.

After admission, it starts the110-input native review and its own bound20k
three-case benchmark preflight. Only a successful preflight permits the full
3,162-case benchmark. Its deadline is48h, with40GiB start/24GiB runtime RAM and
192GiB disk reserves; failures stop explicitly without retry. Numerical/native
render completion, actual image viewing and history publication remain separate.

The bound offline worker then independently audits every complete primary
photometry/CFA row and runs the **unchanged broad weak-band analysis** previously
used for V131:427 photos, three priors/all CFAs,5,124 matched observations,
96,075 unique16px GT blocks. It preserves the native240px interior, DCT annulus
[1/8,1/3), original eligibility/contrast masks, independent FFT check and
source balancing. This complements the repeated four-material faint subset;
no synthetic or camera reference is silently counted as photo GT.

Publication still requires the actual completed results, independent audits,
native crop inspection, both protected GFX reviews, source-bound history update
and reconciliation of guidance. The [scene2k full427 benchmark](whole-scene-context-primary-admission.md)
continues separately; its already-completed camera scores are not copied to the
new scaling model. [Current training and actual corpus coverage](full-corpus-scaling.md).
