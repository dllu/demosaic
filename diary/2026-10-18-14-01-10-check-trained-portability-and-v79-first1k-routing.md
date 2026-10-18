# Check trained portability and V79 first1k loss routing

Previous goal turn made progress by closing V78's original 4k training and
checking the V79 handoff. Revalidated controller 404904/1792353195.14 and V79
child 444533/1792356217.53 live, plus evaluator/closure/reference/boundary owners.
The original schedule and frozen inputs remain in use. No training restart,
retuning or intermediate quality-based decision.

While the GPU trained V79, checked the actual trained V78 EMA on CPU with two
threads and CUDA hidden. Current package bytes exactly match the frozen training
package. The public inference loader restores all 99 EMA tensors, including
eight learned nonzero directional tensors. Exported an EMA-only inference copy
and reloaded it through the same API; all registered state and official DINO
weights agree. Both produce bitwise identical FP32 outputs on generated native
64px inputs across RGGB/BGGR/GRBG/GBRG, including signed black/ADC-white patches.
Auxiliary CFA matches explicit sampling. Registered state and Torch CPU RNG are
unchanged through forward; CUDA remains uninitialized. This is unscored
engineering input, with no photograph/GT or model-quality/16-bit/full-frame/speed
claim. The private inference copy is not a promoted checkpoint. Both loads use
the pinned approved DINO cache.

The two output NPY hashes agree:
`99c24d7b4e75ea2d4b0cedde16e253003c937d38d0dbf5d5b01458c8c70486a8`.
The EMA-only checkpoint is
`df230d9f234ba2efdd3877c5bc194b7e60bc70ec03ee32e39a0c8138641663ce`.
The exact private executed source, plan, inputs, output arrays and model hashes
are retained under `.cache/benchmarks/directional-V78-portable-CPU-v1/`.

V79 completed its first 1,000 updates and the watcher retained checkpoint
`53aa8d050a30ce357ada48a62e99d75607c819e3d95c27c6b2efbd5cc17e3725`.
All 99 model / 99 EMA / 97 AdamW states are finite with correct counters/shapes;
all 25,800 directional scalar moments are nonzero. The first 56 complete sampled
records match control exactly, and all 41 first1k logged step/domain/LR/full-batch
hashes match. Snapshot these prefixes rather than hashing a live growing log.

Verified the actual optional-loss routing: 18 Commons/procedural and 12 native
synthetic logged rows contain the interval term; 11 paired rows omit it. NumPy
FP32 multiplication/addition reconstructs all 60 nonpaired first1k logged total
losses across both arms exactly (maximum error 0), using the frozen base weights
and candidate interval weight .1. This confirms scalar accounting while the
earlier small cross-process base-loss variation remains a separate limitation.
It does not demonstrate better images, isolate GPU kernel causes or estimate
seed uncertainty.

No application/model/training source changed; verification uses existing APIs
and preserves all fixed criteria. V79 continues the original 4k budget; final
quality, native viewing, publication audit and any eligible full-frame/16-bit/
timing review remain outstanding. Goal remains active and unmet/unproven; V43
stays the working reference. No new tests or broad suite reruns were needed for
this documentation/runtime-evidence change.

See [updated handoff report](../docs/directional-v78-original4k-training-handoff.md)
and [bound receipts](../docs/results/directional-portable-and-V79-first1k-v1.json).
