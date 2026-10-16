# Reviewed paired-data admission

New paired scenes require an exact, hash-pinned review before the training
loader can accept them. The registry is currently empty: **no new paired data
is admitted yet**. The original32-scene route keeps its sampling behavior.

The embedded review payload records acquisition, protected/Commons screening,
prepared-target and manual-review SHA256s; protected scene names; and every
approved case including its noise conditioning, camera metadata, references
and absolute crop paths/hashes. Canonical JSON determines its review hash.
The loader accepts only an exact hash explicitly registered after review.
Self-signing a receipt or changing a quarantine split does not register it.

New cases must match their complete reviewed records. Unknown cameras,
EOSM100/GH1 aliases, existing train32 IDs, protected names and the conservatively
excluded scene families are rejected. Missing or duplicated reviewed cases,
changed conditioning/WB/path and corrupted NPZ files also fail. This contract
supports a later separate opt-in extension; it does not modify current recipes,
base/quarantine manifests, held-out data or private frozen training source.

Fifteen focused admission cases are covered by the CPU suite, which passes
**427 tests with eight CUDA checks skipped** in62.57s. Genuine GPU checks remain
queued behind capacity training in their separate frozen source. This count
does not claim those queued GPU checks ran on the newly added loader contract.

[Actual train32 compatibility receipt](results/paired-admission-legacy-parity.json):
the original immutable manifest,32 scenes, seed48 and native256 patches yield
identical tensors and SHA256s for ten declared indices under the previous
frozen loader and the new loader. Source versions and the driver are archived;
CUDA was not initialized. This is routing/sampling compatibility evidence,
not restoration quality or a new data admission.

The [expanded quarantine](paired-extension-quarantine.md) is still undergoing
native target/alignment review before a review hash can be registered.
