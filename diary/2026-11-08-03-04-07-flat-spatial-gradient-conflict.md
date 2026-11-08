# Flat spatial gradients oppose paired detail through shared weights

Recorded: 2026-11-08T03:04:07-08:00 (America/Los_Angeles).

The previous turn was progress: V181 completed its matched training, audits,
actual native viewing, exports and publication, pushed as15e635c9. This turn
checks its detail/quiet tradeoff through local gradients rather than claiming
the useful quieter recipe solves the fine-cab/sky goal.

V182 completes20 native four-image training-only forwards and76 parameter
backward evaluations at the completed raw V180 and V181 checkpoints. Fixed
selection precedes all diagnostic forwards: first/middle noisy batches in each
domain, rows1/505 mesh,5/433 weak,2/478 photo,4/529 mixed,8/553 flat. The original
owner PID916635/create1794135260.11 is terminal, with20wrapper/frozen/network/
projection calls and100samplers. There are zero optimizer updates,new source/
noise,parent/DINO,RAW decode or protected inputs. All98 neural files remain
unchanged. Both model/frozen states and RNG snapshots taken after construction
remain exact during their probe loops. Peak allocation6.6307GiB; the existing
atomic sampler backward remains warn-only nondeterministic.

The new spatial term and paired-difference loss have positive output-gradient
cosines on all12 paired cases, but negative parameter cosines on10/12 in both
Euclidean and fixed saved-Adam metrics. Negative added-spatial directions lower
the target-pair response functional on all12 cases in the fixed metric. Shared
network parameters alone have the same12/12 sign, evidence-adapter parameters
alone10/12. The original seven-term negative direction increases response on
10/12. Clean-mask eligibility and direct output alignment do not prevent
shared-parameter suppression. The fixed metric excludes actual Adam first/new
second moments,clipping,decay and finite/cross-batch effects; these derivatives
do not prove a finite training benefit or a cause of all V181 quality differences.

Added-spatial/original-total gradient norms in that metric range0.104–0.549 on
the paired batches,2.131–4.189 on mixed and1.046–2.528 on flat batches. These
are two selected batches per domain at two states, not population estimates.
Full-target pair response is not a fine-band score. Independent target DC
energy fractions are below7e−11 on the six unique paired target batches, so
constant target offsets have negligible energy here. Cross-batch gradient
interactions remain unmeasured. Prepare coherent pair-response supervision
alongside existing flat/absolute losses; do not infer an optimizer change or
new real-photo quality from this diagnostic alone.

Twenty-two helper/response/geometry CPU checks and four independent-auditor
checks pass; the earlier18-check pure-math prefix is retained. Strict CPU
readiness restores both raw checkpoints,284 Adam denominators and4,184,052
trainable coordinates with every neural Module call forbidden. All5,700 actual
layer/output Grams have independent NumPy/Torch FP64 checks; the maximum
error is0.000843 of the fixed tolerance. All20 native RGB batches are retained,
as are full first-mesh parameter gradients and denominator diagonals at both
checkpoints. Other vectors retain fingerprints and in-process checks.

The independent CPU audit passes53,477,376 saved RGB channels,all bindings,
20 FP32 totals,masks/spatial losses,24 paired losses,12 response functionals,
140 geometry matrices,two strict raw states,284 Adam denominators,284 retained
layer fingerprints and568 retained Grams. Maximum loss error is3.755e−8;
response error5.551e−17. The first audit stopped after one batch because its
local pair-unit array shadowed the full unit-row list. Exact source,seal/log
remain at audit-work-v1/audit-source-v1/independent-audit-v1. Corrected v2 only
renames that variable and version bindings; a source-difference assertion passes.
No worker,loss,mask,gradient,tolerance,input or successful neural prefix changes.

Actually viewed both plot versions at original detail. The first legend covered
the final paired row; separately frozen v2 adds bottom axis space for the legend,
using identical measurements. All twelve rows remain visible. Public PNG/SVG
copies match that viewed v2 exactly. Plot sources,render receipts and first
layout remain preserved. The full public evidence records all20 rows, per-layer
Grams/fingerprints,plans,checkpoints,CPU readiness,first audit failure,and sources.

V180/V181 quality recommendations and actual native crop evidence remain
unchanged. Both protected GFX families,JPEGs and siblings stay excluded from
training; originals and unavailable /mnt/dataz remain unused. Existing fine
cab ROI/profile/JPEG views, main sky/building/foliage/coarse fence and native
triplets remain in the V181 report. Independent ISO100/AHD/JPEG references are
qualitative, not exact GT. The joint fine-detail/quiet-field goal remains active.

[Diagnostic and actually viewed plot](../docs/flat-spatial-gradient-conflict.md) ·
[Full machine evidence](../docs/results/v182-flat-spatial-loss-geometry-v1.json) ·
[Publication verification](../docs/results/v182-flat-spatial-gradient-publication-verification-v1.json) ·
[Actual V181 quality](../docs/flat-spatial-evidence-comparison.md).

