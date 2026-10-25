# Native-data comparison: engineering and launch record

The [fixed V84/V85 study](native-data-v84-v85.md) compares the reviewed native
extension against the existing native corpus, starting both arms freshly from
the genuine V63 original20k EMA. Only native membership and output paths differ.
No architecture, loss, Commons selection or augmentation changes accompany it.

Both arms completed their original 20,000 updates by 2026-10-19 19:50 UTC,
and both trainer owners and the training controller exited successfully. The
queued review independently loaded the genuine final states: finite
91-model/91-EMA/89-AdamW states, every optimizer counter 20000, and matching final
Python/CPU/CUDA RNG states. All 595 recorded Commons/paired input pairs match;
all 221 recorded native pairs change. Each arm has 801 finite logged training
rows with the declared original-horizon LRs. Closed `last.pt` and retained final
checkpoint bytes match within each arm. Unrecorded inputs are not independently
replayed. [Final training receipt](results/native-data-original20000-completion-v1.json).

The expanded final SHA256 is
`44d46580d1026f8581e4a9404dbd7c3eed9721459cf19edd1efecdc266594c57`;
the control final SHA256 remains
`134887e12357aabf420cceee3ee53fc8832cf02a8f81ff883b829a9e51e16f10`.
The complete [original20k quality and native review](native-data-original20k-review.md)
has now finished. Expanded−control photo PSNR is −0.00422dB, with a source95%
interval spanning zero. Both arms fail known-camera eligibility and both weak
carrier gain requirements; four ADC layout/draw contrasts exceed the declared
loss ceiling. All eight final boards were actually viewed. Those original
study-specific gates do not erase the useful gains over V43/V63: the final
review establishes the V84 architectural family used in
[current model choices](current-model.md). The earlier progress checks below
retain their original engineering scope.

Both discarded engineering checks passed 16 actual updates per arm, using the
original20k schedule. CPU used B1/native64/FP32; CUDA used the intended
B16/native256/BF16. An independent checkpoint read verified finite91-model,
91-EMA and89-AdamW states, optimizer steps16, actual owner exits and identical
final Python/CPU/CUDA RNG states. All44 training-core files and the controller
match their frozen preflight bytes. The initial parent EMA and official frozen
DINO identities match between arms.

Each check observed15 identical shared-domain batches and one native batch.
The CPU draw happened to use unchanged legacy data; its native inputs matched.
The CUDA native inputs changed, exercising the treatment at the intended batch
size. This is initialization, data-path and execution evidence, without a
trained-quality conclusion. [Audited receipts](results/native-data-v84-v85-preflights-v1.json).

The preserved first CPU attempt failed before updates because a relative plan
path was resolved inside the frozen working directory. The controller now
resolves that path before child launch. The successful CPU check used a fresh
root; the failed plan and logs remain intact. Six focused observation-guard
tests and Ruff pass. No neural or training-core implementation changed.

The control completed its original 20,000 updates and exited successfully.
Its retained final checkpoint SHA256 is
`134887e12357aabf420cceee3ee53fc8832cf02a8f81ff883b829a9e51e16f10`.
A read-only endpoint check verifies finite 91-model/91-EMA/89-AdamW states,
all optimizer counters at 20000, the original schedule's 1e-6 final LR and 10% floor,
all 801 logged batch hashes/LRs, 816 observed domain choices and the source digest.
The retained final copy and closed `last.pt` have identical bytes.

The expanded arm started serially after the successful control exit and stable
memory gate, with actual owner 3666689 / creation 1792421187.78. Its first 17
recorded observations through step 25 include 16 exactly matching Commons/paired
batches and one changed native batch. That handoff checked the intended input
treatment before the final checks above.
[Endpoint and actual handoff audit](results/native-control20000-expanded-start-v1.json).

The same receipt now includes a closed retained 4k follow-up, after the expanded
trainer passed step 4025. Both arms have finite 91-model/91-EMA/89-AdamW states,
all optimizer counters at 4000 and identical optimizer groups and Python/CPU/CUDA
RNG states at that boundary. LR 9.206544616434249e-6 matches the original 20k
schedule and 10% floor. All 130 logged shared-domain pairs match; all 46 logged
native pairs differ. Source archives differ only in the native manifest. This
was an engineering check; it did not substitute for the final endpoints or
quality review.

The closed retained 10k pair also passes. Both have finite 91-model/91-EMA/
89-AdamW states, counters at 10000, identical optimizer groups and Python/CPU/CUDA
RNGs, and LR 5.571396837256637e-6 from the original 20k schedule with its 10% floor.
All 305 logged shared pairs match and all 111 native pairs differ. Each arm's
401 logged training rows match batch hashes/LRs with finite loss/gradient norm;
unlogged examples are not independently replayed. Source digests reconstruct,
archives differ only in the native manifest, and all 253 runtime hashes remain
exact. The first read-only attempt stopped at its initial safety guard before
checkpoint IO; the completed check waited for stable memory headroom. The same
public receipt preserves both observations. Final endpoint and quality requirements
are unchanged.

The original 20k production controller and expanded trainer run from
commit `650a051`. The plan binds 253 frozen runtime files and 748 fixed input
references, including the737 data/provenance inputs and engineering receipts.
[Dated live-owner launch snapshot](results/native-data-v84-v85-launch-v1.json).
Each arm must pass the declared memory and disk gates. Runs are serial,
with no automatic retry, extension or promotion. Final quality and native crop
reviews have completed as linked above. Current recommendations follow the
measured strengths and weaknesses in the model guide.

The retained control 10k checkpoint now passes a
[read-only midpoint engineering audit](results/native-control-retained10k-engineering-v1.json)
after training advanced beyond its closed copy. All 91 model/91 EMA tensors and
89 AdamW parameter states are finite, with every optimizer counter 10000.
The LR is 5.571396837256637e−6, independently matching the original 20k cosine
with its 10% floor. All 416 recorded domain choices match the declared selector;
401 logged training rows match their observation hashes/LRs and have finite
loss/gradient norm. All 44 archived package files and 253 frozen runtime files
remain exact; the original data/protocol and source-snapshot digest match.
This checked state and recipe integrity without inference or interim quality
selection. It did not substitute for the original 20k endpoints or the complete
final review.

The full review adapter has independently checked both genuine16-update
CPU/CUDA checkpoint pairs, including91/91/89 states, original20k schedules,
source-manifest-only archive differences and shared/RNG equality. It rejects
live production and refuses engineering boundaries as quality results. An
unchanged historical primary-score replay reproduces the original per-arm and
matched thresholds; the new names describe generic scorer positions in that
replay. At review-preflight time, no V84/V85 held-out predictions had been made. The analytic reviewer
keeps all192 individual ADC layout/draw contrasts and12 group means, alongside
the two existing weak-carrier/flat requirements. A loss in one case cannot be
hidden by averaging. [Review preflight](results/native-data-review-preflight-v1.json).
Eleven new focused guards and33 related review/lineage tests pass; Ruff passes.

The shared panel engine retains its existing internal status names. The new
adapter binds V84/V85 original20000 labels, genuine completed training owners,
91/91/89 states and the original20k hue lineage. The queued CPU closure uses
the new data-study scorer while retaining the existing saved-array, native-pixel
and V43/RawNIND reference checks. Actual native viewing remains required.
[Actual queued owners and source bindings](results/native-data-v84-v85-review-queue-v1.json).
At launch, all three waiters were verified childless, without Torch/CUDA mappings,
with no model outputs created while training was live. Review uses257 frozen files;
all44 package files match the actual training runtime exactly.

The separate Commons recovery has completed both cache scales and protected
screening. Reconciliation and the bounded archive download have finished; all
4,557 subsequent originals pass size/SHA1 verification. These download arrivals
remain outside both arms and require admission review. The separately
[reviewed 890-source extension](commons-local1188-reviewed.md) is available for
a future frozen recipe. This comparison does not change the Commons corpus.
