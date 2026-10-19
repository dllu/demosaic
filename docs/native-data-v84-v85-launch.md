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

The original20k production launch will bind the committed criteria, manifests,
737 fixed data/provenance inputs, engineering receipts and frozen runtime
sources. Each arm must pass the declared memory and disk gates. Runs are serial,
with no automatic retry, extension or promotion. Final checkpoint quality and
native crop reviews remain outstanding; the README stays on V43.

The separate Commons recovery has completed both cache scales and protected
screening. Reconciliation has finished and the bounded archive downloader is
running. These new arrivals stay outside both arms pending independent content,
duplicate and split review. This comparison does not change the Commons corpus.
