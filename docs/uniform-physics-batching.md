# Batch physical operations for a shared inference noise prior

An isolated CPU prototype produces identical physical fields and genuine V63
predictions while reducing repeated Python calls for a scalar shot/read prior.
The production model and the running V90/V91 training/review remain unchanged.
There is no GPU timing or full-frame speed result yet.

[Executed sources, inputs, checkpoint, arrays and comparison receipt](results/uniform-physics-CPU-v1.json).

The current stabilized forward loops over images for the GAT, initial MHC
demosaicing and expectation inverse, even when `set_noise` receives one scalar
profile for the whole tile batch. The prototype applies each operation to that
batch directly. Per-image normalization, physical anchors, frozen DINO, neural
precision, prediction and inverse expressions remain intact. The original
multi-profile branches remain verbatim in the generated AST, including a vector
containing equal profiles. This is an inference engineering experiment without
an optimizer, new weights or a quality claim.

## Executed CPU checks

The probe generates its candidate forward in memory from the hash-guarded
current method. Replacing its two changed subtrees with their originals must
reproduce the complete original AST exactly. Both method sources, all47 model
modules and the executed driver are preserved under
`/mnt/external/demosaic/experiments/uniform-physics-CPU-v1/`.

All48 component cases pass exact byte and stride comparisons for four returned
fields: transformed measurements, noise proxy, initial RGB and inverse RGB.
That covers192 fields/378,048 values. Cases include pure Poisson, shot/read,
read-dominated, Gaussian and ADC-only priors; scalar B1/B4; both memory layouts;
even/odd packed extents; negative measurements; all four Bayer patterns in B4;
per-image WB; and mixed/equal-vector fallback profiles. Component inputs are
deterministic nonphotographic fields.

The genuine V63 original20k EMA then runs on the same four cached GFX subcontexts
used by the earlier physics cleanups: native80×64 at relative
`[216,224,80,64]` inside the saved512px contexts. All184,320 complete RGB values
are byte-identical across scalar GFX noise, equal-vector fallback and scalar
ADC-only conditioning. All model/DINO state, parameter identities and RNG remain
unchanged; CUDA stays hidden and uninitialized.

Checkpoint SHA256:
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
GFX shot/read variance:
`.0014635775921166604 / .0000010715704128646712`.
No reference image, GT score, training objective or source-drive access occurs.
This does not establish equivalence at the full512px serving context size.

Measured Python calls for the four-context genuine forward:

| Conditioning | Operation | Original | Prototype |
| --- | --- | ---: | ---: |
| Scalar GFX | MHC |5|2|
| Scalar GFX | GAT forward |8|5|
| Scalar GFX | GAT inverse |4|1|
| Equal-vector fallback | MHC / forward / inverse |5 /8 /4|5 /8 /4|
| Scalar ADC-only | MHC |5|2|

The ordinary camera preview still needs one MHC call. Four scalar GAT white-anchor
calls also remain. These are Python call counts, not device kernel counts or
latency measurements. Batched MHC can use different CUDA convolution algorithms
and larger intermediate allocations; CPU agreement does not settle GPU
numerics or peak memory.

An independent NumPy read verifies every saved full-model array's dtype, shape,
finiteness, hash and byte equality. All66 receipt references verify. The scalar
GFX baseline also matches the earlier inverse/physical cleanup's saved output
exactly, file SHA256
`425cc15ec6282b5caed94f64387efaf3e43d4608710094a122495ef8dc17dcad`.
Ruff passes. No additional project tests or GPU jobs were started.

## Reproduction and remaining measurement

```bash
source scripts/env.sh
CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONPATH=.:src:scripts \
  uv run --no-sync python scripts/probe_uniform_physics_cpu.py \
  /mnt/external/demosaic/experiments/CHOOSE-NEW-CPU-OUTPUT
```

The existing output is immutable; a new execution needs a new directory. The
probe checks memory/disk headroom before loading the model. Future CUDA work
must wait for the exact training and complete quality-review owners to exit,
then compare unchanged-weight predictions at actual serving dimensions and
measure both policies with the same precision and inputs. The existing
1DN16 maximum/.25DN16 RMS full-output gate should remain unchanged. No production
integration follows from this CPU result alone.
