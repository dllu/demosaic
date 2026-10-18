# Mixed-domain optimizer batches

The trainer can now average consecutive original source groups before one
gradient clip/Adam/EMA update. Source indices, per-group target masks and noise
draws retain their original data-step identities. Existing recipes default to
one group and keep their previous update behavior.

```yaml
batch_size: 4
optimizer_batch_groups: 4
optimizer_forward_groups: 1
data_seed_per_step: true
```

This gives an effective batch16 through four B4 forwards. Forward groups2 or4
join original groups into B8/B16 forwards, retaining each group's original loss
reduction. A single gradient clip follows the accumulated mean. Grouped updates
currently require the packed backbone and stateless per-data-step degradation.
Only selected source groups are fetched; unused-domain loaders remain lazy.

`steps`, `warmup_steps`, checkpoint/log intervals and `--stop-after` count
optimizer updates. Data samplers and degradation RNG instead use original source
steps. Checkpoints record both data steps and example draws; resume rejects
changed group layout, source batch size, EMA decay or inconsistent counters.
Logs retain per-group domain, source step, example count and optional fingerprint.

## GB10 execution comparison

The [completed sweep](results/packed-isotropic-mixed-execution-CUDA-v1.json)
compares the same effective16 across B4/B8/B16 forwards, using actual frozen
training observations, gain32/residual÷32, IEEE FP32 and channels-last. Fresh
models use four excluded warmup updates and16 timed updates per point.

| Model | B4 accumulated | B8 accumulated | B16 joined |
| --- | ---: | ---: | ---: |
| No-DINO, examples/s | 14.577 | 13.469 | 12.067 |
| DINO, examples/s | 13.764 | 12.951 | 11.527 |
| No-DINO peak allocated GiB | 4.743 | 9.238 | 18.234 |
| DINO peak allocated GiB | 4.876 | 9.399 | 18.434 |

Four B4 forwards are fastest for both arms, about20% faster than joining16 in
this compute comparison. The predeclared common choice minimizes combined time
for the two models. Timing includes forward, group losses, backward, clipping,
optimizer and synchronization; it excludes loading, augmentation, degradation,
transfers and initialization. These are shared-machine observations, without a
repeat-study confidence interval or full-data throughput claim. Initial outputs,
all optimizer states/gradients and genuine frozen DINO hashes verify; fixtures
remain unchanged and learned benchmark weights are discarded.

106 targeted checks pass, including real mixed-data stop/resume for all three
layouts, unchanged source/noise fingerprints, clipping after accumulation,
nonzero-head gradient equivalence and the CUDA data-RNG isolation check. The
default loop also matches its archived CPU training loop's weights, EMA, Adam
moments and RNG exactly on the integration fixture.

The new V72/V73 recipes use effective16 through B4 accumulation, fixed units and
FP32. Their full640,000-example horizon is40,000 optimizer updates; the first
32,000-example gate is2,000 updates, warmup8,000 examples is500 updates and
EMA cap is`.999**4`. The first12 genuine updates are checked and continued with
full state, preserving the schedule. They retain the old data manifests and
change units, precision and optimizer grouping relative to V70/V71; this is an
exploratory candidate, not an isolated ablation against those older models.
Only DINO presence/fusion differs within the new pair. Full quality review and
native crop triplets remain required before any promotion.
