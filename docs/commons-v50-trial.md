# Test the larger Commons corpus with the retained architecture

[V50](../configs/dino-commons-expanded-b16-v50.yaml) changes only photographic
Commons membership versus completed V47:40,170→52,536 training sources. This
includes the preceding1,808-image extension plus10,558 newly reviewed sources.
All old cache records and2,303/2,255 validation/test identities must remain exact.
The [data review](commons-incoming-v2.md) keeps188 protected matches quarantined,
reserves new holdout buckets and excludes duplicates. Finite identity checks do
not prove complete scene disjointness.

Use the original frozen DINO recipe: V43 first1000 EMA, fresh AdamW/EMA, seed50,
B16, LR3e-5/planned3000 and first1000 gate. Native128/paired32,25/25/50 mix,
4×→geometry/PSF→2× targets, original8× validation, camera projection and original
full-resolution/precision remain fixed. Rank4 adaptation and matrix centering
remain off after their negative reviews. No source implementation changes.

The guarded queue must wait for matching4× preparation, all10,558 new cache
SHA256s and the separate freeze, plus actual V49 controller exit. It verifies
the new frozen manifest/audit identities, all44,728 original active4× records,
training-only additions and the exact V47 source/parent/config comparison before
training. It binds the final manifest hash in its training plan when ready.

The photo draws legitimately change. Logged paired/native input/target hashes
must remain identical to V47, with the same domain schedule and independent
per-step data RNG. The full first-gate review then includes known/unseen paired
data,427 photos/16 procedural sources, two exact synthetic-GT native crops and
full102MP GFX sky/building/foliage/fence with verified RGB16 files. Reuse the
cached V47 evaluator only after exact source/protocol/classical-case checks.
More data alone does not establish a gain. V43 step2000 remains the current
photographic experimental reference until a complete comparison supports a change.
