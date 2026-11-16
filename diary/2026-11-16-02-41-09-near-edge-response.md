# Evaluate fresh-noise finite-wire response near strong edges

Recorded: 2026-11-16T02:41:09-08:00 (America/Los_Angeles).

Built an evaluation-only finite-wire panel with eight new procedural sources,
near/far strong edges, all four CFAs, zero/one/two-direction roles and independent
noise per role/repeat. Geometry precedes2× area reduction; no protected images
or original photos are read. The exact parent pipeline reproduces an old512px
batch bit-for-bit. All193 anchor tensors agree across V200/shared raw/EMA;
9,437,184 delivery channels match actual full forwards on the first RGGB batch.

Completed128 batches/384 observations and2,688 metric rows, including final-head
gain sweeps relative to V195. The weaker conditional response is output(two)
minus output(one), projected on the actual weaker clean increment. Shared EMA
response is0.9913% near/1.4946% far, versus V200 EMA0.9923%/1.4958%. Small quiet
gains persist, but paired source intervals include zero weak-response difference.
The new head's substantial extra response is primarily to the stronger family.

Two noise draws per CFA plus source clustering separate image counts from
independent sources. Noise and output variation remain significant; a hidden-
template sensor calculation gives median pair SNR2.15 near/2.79 far. This is not
unknown-wire detection power and does not prove architectural incapacity.

Retained the original difficult condition and launched lower-noise profiles
0.00032/4.096e−7 and0.00008/2.56e−8 sequentially with identical clean targets.
Snapshots and process identities bind both runs; there are no automatic retries.
The added profile API preserves the exact clean/camera fields in tests.

Published four native160 exact-GT triplets/five-column boards and four averaged
increment diagnostics. All eight boards were actually inspected. Increment
views amplify128around neutral0.18 and average fourCFAs×two draws; they are not
single restored photos. Source/error/uncertainty bindings and frozen evaluated
code are preserved. Tests cover independent noise, RNG preservation, all CFAs,
counterfactual scoring and correct source-cluster accounting.

[Report](../docs/near-edge-response.md).

Final verification passes36 tests and Ruff, checks exact archived bytes and
native crop sizes, and verifies all128 ISO1600 clean target/camera/mask batches
bit-for-bit against ISO6400. A standalone replay initially used different CPU
reduction threading and differed by up to1.49e−8; the frozen two-thread runtime
reproduces every array exactly. No scientific prefix was restarted or replaced.
ISO1600 completed; the same controller is now running ISO400. The full SNR
comparison remains pending.

