# Native-data comparison: engineering and launch record

The [fixed V84/V85 study](native-data-v84-v85.md) compares the reviewed native
extension against the existing native corpus, starting both arms freshly from
the genuine V63 original20k EMA. Only native membership and output paths differ.
No architecture, loss, Commons selection or augmentation changes accompany it.

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

The original20k production controller and control trainer are running from
commit `650a051`. The plan binds253 frozen runtime files and748 fixed input
references, including the737 data/provenance inputs and engineering receipts.
[Dated live-owner launch snapshot](results/native-data-v84-v85-launch-v1.json).
Each arm must pass the declared memory and disk gates. Runs are serial,
with no automatic retry, extension or promotion. Final checkpoint quality and
native crop reviews remain outstanding; the README stays on V43.

The full review adapter has independently checked both genuine16-update
CPU/CUDA checkpoint pairs, including91/91/89 states, original20k schedules,
source-manifest-only archive differences and shared/RNG equality. It rejects
live production and refuses engineering boundaries as quality results. An
unchanged historical primary-score replay reproduces the original per-arm and
matched thresholds; the new names describe generic scorer positions in that
replay. No V84/V85 held-out predictions have been made. The analytic reviewer
keeps all192 individual ADC layout/draw contrasts and12 group means, alongside
the two existing weak-carrier/flat requirements. A loss in one case cannot be
hidden by averaging. [Review preflight](results/native-data-review-preflight-v1.json).
Eleven new focused guards and33 related review/lineage tests pass; Ruff passes.

The shared panel engine retains its existing internal status names. The new
adapter binds V84/V85 original20000 labels, genuine completed training owners,
91/91/89 states and the original20k hue lineage. The queued CPU closure uses
the new data-study scorer while retaining the existing saved-array, native-pixel
and V43/RawNIND reference checks. Actual native viewing remains required.

The separate Commons recovery has completed both cache scales and protected
screening. Reconciliation has finished and the bounded archive downloader is
running. These new arrivals stay outside both arms pending independent content,
duplicate and split review. This comparison does not change the Commons corpus.
