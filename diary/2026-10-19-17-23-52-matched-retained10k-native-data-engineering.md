# Matched retained 10k native-data engineering check

Previous goal turn made progress by retiring verified duplicate Commons cache
bytes, preserving exact filename/index/manifest bindings. This turn revalidated
the same expanded trainer3666689/1792421187.78 and controller3343889/1792403189.77,
then monitored from7825 through10025. Recorded loss/gradient values stayed finite;
RAM was generally58–63GiB and root free space roughly153–154GiB. Training was
neither stopped nor restarted. Final quality/SOTA/speed objectives remain open.

The first CPU audit stopped at its initial exact-owner/48GiB-resource guard
before checkpoint IO. Subsequent actual owner revalidation showed the same live
trainer at10150 and53.39GiB available RAM. The failed guard observation is
preserved rather than treated as a failed training job. A read-only retry waited
for30continuous seconds above48GiB before loading either closed checkpoint.
No CUDA initialized and no model inference or quality selection occurred.

Both retained10000 files have finite91-model/91-EMA/89-AdamW states, each model
and EMA containing32,904,710 elements. All optimizer counters are10000 and second
moments are nonnegative. Optimizer groups and Python/CPU/CUDA RNG states match
exactly at this boundary. LR5.571396837256637e-6 matches an independent replay
of the original20000 cosine with its10% floor. Both preserve genuine V63
original20k initialization, B16/native256/BF16, seed53, deterministic execution,
sensor-valid supervision and4x→geometry/PSF→area2 augmentation.

All416 recorded pairs are compared:305 shared Commons/paired batches match
exactly and111 native batches differ. For each arm, all401 logged training rows
match observation hashes, original LRs and finite losses/gradient norms.
Unlogged observations are not independently replayed. Native memberships remain
128captures/106groups versus150/120; fixed Commons/paired/validation manifest
bytes match their source archives. Both source digests reconstruct exactly,
and the archives differ only in raw-clean-manifest.json. All253 frozen runtime
hashes remain exact. The retained files' bytes and mtimes stay unchanged.

Control retained10k SHA9058a2404d0da190084ca7db501edb657560c3ccb8ab5c527db5a7fe656d5a7c;
expanded SHA c22ec73863eb71bb8ba559fecc34294d50f7a576a80d414695bc9780070c03bb.
The expanded trainer had reached10275 before the successful audit. Full states,
original schedule and sampled data coupling are verified; this is not a trained
quality claim. Both final20k endpoints, final RNG equality and complete numerical
and native-crop review remain required. V43 remains the working reference.

The executed retry driver, first guard observation and completed receipt are in
.cache/benchmarks/native-control20000-expanded-start-v1/ (driver at
.cache/audit-native-retained10000.py). The existing public endpoint receipt and
unbound launch record now include this midpoint. Bound study criteria, runtime,
inputs and budgets are unchanged; the full goal remains active.
