# V143: more learning on weak lines with smaller gradient smoothing

**Fresh5,000-update training from V120 is running. The first 1,000-update
review finds no clear mesh recovery and weaker faint scores.**
It combines V142's crossed-line/empty data with V141's smaller gradient-error
smoothing and retains1,000/2,500-update checkpoints for early comparisons.
[Native/GFX/flat progress report](v143-progress1000-quality.md) includes two
exact synthetic-GT triplets, both protected scenes and the verified flat review.
V120 remains recommended. The endpoint and 2.5k quality are still unmeasured.
[V142's completed review](v142-crossed-line-pilot.md) motivates keeping the data:
modest faint/weak-band and noisy-flat spatial gains, with unresolved mesh,
coarse noisy error and selected ADC-only color bias.

[Actual checks, process identities and fixed review plans](results/v143-crossed-gradient5000-setup-v1.json) ·
[Recipe](../configs/quality-v120-crossed-gradient5000-v143.yaml).

## The candidate and its limits

V143 starts freshly from V12020k EMA. It keeps90,782 photos/27 reviewed regions,
seed70,50% reviewed quota,native256/B16/BF16,zero optical PSF,LR1e−5 and100 warmup
updates. Mesh/empty sources occupy.10 of the existing.15 weak procedural quota,
with half absent. Pixel Charbonnier epsilon stays.0003; rendered-gradient error
epsilon becomes.00003. All loss coefficients and the paired objective stay fixed.
The official DINOv3 Small encoder remains frozen.

The original cosine horizon is5,000, with checkpoints every500 and immutable
progress captures at1,000/2,500. The same worker continues to5,000. These retain
weights without extra model calls or optimizer updates. Compared with V1421k,
this changes both gradient smoothing and learning horizon; the post-warmup LR
curve differs. It cannot isolate either cause or provide an equal-budget claim.
A longer run tests whether the useful new data can teach more detail; it does
not guarantee fence recovery or flat-region safety.

CPU128/B1 and CUDA256/B16 execute16 fresh+2 resumed updates. Both preserve all91
parent/resumed tensors and official encoder identity, with91 model/EMA tensors
and89 Adam states finite. All18 clean/noisy input hashes match saved V142 in
each check, and4,259,840 initial output values match exactly. Inherited or
invalid gradient epsilon rejects before constructing a resumed model. Production
also checks its first18 inputs against its genuine CUDA check.

## Predeclared quality review

Each1,000/2,500/5,000 checkpoint receives the same102 IEEE-FP32 observations:
64 shadow,16 ordinary,16 faint ADC,four main GFX512 contexts and two additional
mesh768 contexts. Reuse V120,V129,V141 andV142 predictions, with unchanged
source masks, ROIs, CFA layouts, noise draws and display transforms. Both
protected GFX pairs, foliage/fence/sky/building regions, both extra-mesh priors
and camera JPEGs remain included. Independent ISO100/AHD/JPEG references are
qualitative comparators, **not exact GT**.

Each point also receives the same48 exact analytic uniform fields, reusing
V120/V142 controls, and the original two-window/ten-peak mesh-power diagnostic.
The peak extension reuses its primary outputs and adds no inference. Each point
therefore uses150 candidate root/DINO calls and504 cached control predictions;
450 candidate calls were originally planned across all three points. There are no new
noise observations, RAW decodes or control-model calls in these reviews.
The first flat collector timed out after saving48 predictions but before final
integrity checks. A separately recorded one-call probe and48-call recollection
with one CPU thread passed the complete checks. The first review therefore
used199 actual calls,49 extra; projected total is499 if the remaining reviews
complete. All flat quality uses the fully verified recollection, while the
original failure and outputs remain preserved.

Before collection, binding checks the original producer identity, declared
step/horizon,lineage, all finite91 model/EMA tensors and89 Adam states, exact69
trained-source modules and all first1,000 clean/noisy hashes against V142.
Only that shared prefix is asserted matched; V142 has no later training inputs.
Progress labels preserve the5k horizon and differ from a completed endpoint.
Independent numeric/pixel audits precede actual native viewing and publication,
including at least two noisy/restored/exact-synthetic-GT triplets.

The66-test review suite checks explicit horizon selection, exact saved-control
observation matching, safe method selection/order, every shared-prefix hash,
progress checkpoint contracts, existing queue protocols and retained analyses.
A real [legacy-default replay](results/v143-review-backcompat-v1.json) compares
the archived and expanded preparers on completed V142 inputs:85 frozen files
are byte-identical, and both primary/faint plans match after normalizing output
root paths and independently verifying their derived document hashes. Original
machine receipts and operator bytes remain preserved.

## Live execution

The resource-aware training controller retains a12GiB CUDA cap,32GB available
RAM floor and original8h production bound. The review watcher waits for the
original checkpoint producer and50GiB available RAM, then processes each fixed
point once. It does not restart training or retry a collection automatically.
Training and review status files are:

```text
.cache/quality-20261102/V143-crossed-gradient5000-v1/status.json
.cache/quality-20261102/V143-fixed-reviews-v3/status.json
```

The initial prospective review queue was superseded before any controller or
collector ran, to make the frozen controller's repository root explicit after
relocation. Its bytes remain preserved. The actual frozen v2 module's repository
and control paths were executed and verified before starting the watcher.
The frozen training wrapper differs from its formatted public copy only in
import spacing; their complete ASTs match, and actual checks use frozen bytes.

The v2 watcher stopped on that collection failure. The v3 watcher processes only
the remaining2.5k/5k points with one CPU thread, preserving every original queue.
It does not repeat the1k primary review or change the training worker/budget.
[Recovery evidence](results/v143-progress1000-flat-recovery-v1.json) records
small FP32 differences between original and recollected outputs; the successful
workaround does not establish the timeout's cause.

The [actual first-batch loss diagnostic](crossed-line-loss-gradients.md) finds
that smaller epsilon increases the gradient-loss term more strongly than the
complete corrective output gradient on one dark noisy mesh. This is a selected
initial-batch observation, not learned quality or the cause of regression.

The1k progress conclusion is provisional. Track faint response, correct
mesh structure, coarse flat variation and color bias together. Full427-photo,
camera/color/full-frame quality and useful real fine-mesh recovery remain open.
