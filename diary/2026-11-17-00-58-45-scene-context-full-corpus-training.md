# Whole-scene integration and full-corpus training

Recorded: 2026-11-17T00:58:45-08:00 (America/Los_Angeles).


Implemented scene_data.py, scene_training_data.py and scene_restoration.py:
complete scene camera/noise observations precede exact native crops, with global
D4 only, explicit Bayer phase, input/target/crop fingerprints and independent
counter-keyed recipes. Pooled/spatial adapters share the frozen DINO weights and
retain the existing local encoder/trunk; only the eighth-resolution state gets
the new zero-initialized offset.19 focused tests pass. Actual native256/B4 checks
run two discarded optimizer updates for each mode, with exact initial V120
outputs, finite gradients, adapter learning and exact checkpoint tensor reload.
Actual wrapper calls15 plus3 direct base checks; encoder calls6/11/11; official
DINO unchanged. These are engineering checks, not improved trained models.

The context cohort is native bin4, >=768 short axis and<=4MP:24660 training
sources plus64 development sources. All remain in the later approved90778
cohort; the3 later exclusions from90781 were already too small and ineligible.
Matched no-context/pooled/spatial horizons2000, two scenes/four crops per scene,
are queued. Their data change is separate from architectural context claims.

The user then requested larger-corpus training and pointed to the November17
scale review. Read it and the existing epoch-order/coverage/execution code.
Used the verified sampler rather than rewriting it: fresh full-model V120
continuations at20k/100k, cleaned90778/33,5% reviewed quota, original bin4->
geometry->area2, native/paired25% each and original loss. Full100k LR horizon
1e-5->1e-6/warm100; no repeated20k schedules.100k plans531903 ordinary-photo
visits, five complete epochs plus78013 draws, with all90778 sources covered;
20k/100k first320k slot indices agree. Counts are planned until executed.

Two initial profile admissions refused setup before model construction: outer
run directories were outside the frozen trainer's own root; the next worktree
lacked project/lock/license metadata required by core source snapshots. New
admissions correct both and preserve original plans/source/logs. No neural,
noise or optimizer trial preceded those refusals.

Current V120 native256/B16/BF16 mixed-domain checks each execute75+2 valid resumed
updates.25warm/50timed rates: strict0 14.8157 patches/s, throughput0 24.9631,
throughput2 23.9751. Loader wait9.75%/12.64%/0.56%. Every sampled full input at
steps1/2/6/76/77 agrees across cases;91 model/EMA tensors and89 Adam states
finite, backbone unchanged.231 actual root/encoder forwards and optimizer
updates. Select throughput0; this short profile is not quality qualification
or an end-to-end speed promise.

The production logger's actual6+2 checks cover all three domains and preserve
resumed91 tensors and Adam/global step6->8. Conditions record actual shot/read,
WB and matrix in bounded batches; source/crop metadata stays CPU-side, full
batch witnesses are sampled initially/every1000. A retention mistake left the
six-step receipt pointing to mutable last.pt, subsequently replaced by resume.
Keep original receipts/condition arrays and final8 checkpoint; intermediate6
checkpoint bytes are unavailable and are not regenerated. Production was fixed
before launch: every phase end gets an immutable hardlink, alongside milestones.

The100k trajectory is now running from untouched V120. Controller1144738/
creation1794905716.93, first child1144739/1794905716.96. Latest witnessed step125
while writing this entry. Allocation: long100k first1000; context none/pooled/
spatial2000 each; matched20k control; resume long100k for99000 from unchanged
optimizer/EMA/RNG/epoch state. Parent is not any discarded profiling checkpoint.
Runtime32GB floor,52GiB admission,16GiB CUDA cap, bounded stage deadlines, no
automatic retries or quality-based stopping. Source/crop/corruption coverage is
recorded separately; repeated crops are not called disjoint native information.

Concurrent documentation cleanup/AGENTS changes were read and preserved. Keep
README concise. After each endpoint, training completion, full427/known-unseen
camera scoring, chart registry/history and actual native/fence review must be
tracked separately. The new runs have no eligible endpoint scores to add yet;
V120/V131 remain the latest comparable completed broad measurements. Context
endpoints need an explicit comparable whole-observation evaluation path; do not
insert old/local-only scores as scene-conditioned results. Refresh both GFX
review maps and chart when comparable evaluations complete; preserve coverage
gaps and scoped missing panels honestly. No recommendation or quality gain yet.

[Scaling report](../docs/full-corpus-scaling.md) ·
[Context model/data report](../docs/whole-scene-context-next-test.md) ·
[Scaling admission/evidence](../docs/results/full-corpus-training-setup-v1/publication.json) ·
[Context admission/evidence](../docs/results/whole-scene-context-training-setup-v1/publication.json).

Follow-up: the first1000 updates finished in750.565 measured worker seconds,
with16000 target examples,5045 distinct photo IDs,5294 photographic visits and
5047 source/crop pairs. Immutable phase-end checkpoint SHA256
e72da50252f1de4c76ecf7985d940d4094a6e8b7de0dca50269cc39eb0ba8c54.
The first context launch then failed at output.mkdir because parent directories
were absent, before context model/data/optimizer construction. No trained
context prefix exists to replay. Preserve the stopped controller's receipts.

Review also caught the context preflight's omitted auxiliary mosaic term.
Before context production, froze a new admission with parent-directory creation,
canonical auxiliary supervision, full optimizer/Python/CPU/CUDA RNG and draw
counter checkpointing. All3 corrected actual two-update preflights pass, incl
optimizer state-step2 reload. Original preflight/source bytes remain unchanged.
Remaining allocation plan4954e1a6d221d2244210ddfaa923477723f3fd47a89cb5ad85e2ea19502b16f3;
controller1148040/create1794907294.12, child1148041/create1794907294.15.
Verified exact child live and context-none step125 in the second immutable
progress capture. Context2000x3, control20k and long100k resume99000 stay in
that order; no1000-update prefix replay, LR reset or reuse of discarded checks.

Both setup publications now preserve exact sources, original terminal failures,
plans, profiles and qualification receipts. An independent CPU audit checks
152 original byte archives,834 frozen source members,20k/100k order-prefix
identity, five actual input witnesses across all3 profiles, both scene
preflight versions,1000-step raw/EMA/89 Adam states and all1000 source/crop/
conditioning records. All checks pass. Checkpoint binaries and original image
caches stay local; large unselected upstream manifests are bound, not all packed.
The discarded step6 bytes stay explicitly missing. No new quality scores or
native image viewing were produced by this source/state audit.
