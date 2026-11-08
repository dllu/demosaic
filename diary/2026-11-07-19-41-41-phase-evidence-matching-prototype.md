# Implement measured phase evidence for the matching branch

Recorded: 2026-11-07T19:41:41-08:00 (America/Los_Angeles).

V178 implements a concrete model variant from the V177 within-image phase
split. Four A-selected frequencies per green direction supply80 feature maps:
transported real/imaginary A/B coefficients,log powers,bounded signed complex
cross evidence and native frequency coordinates. A zero80-to-39 pointwise
adapter adds3,120 weights to the local-noise matching inputs. The existing
matching network and frozen V169 component remain. There is no direct wave-to-
RGB output,hard detection cutoff,target/reference or paired forward input.
The waves can extend beyond true support;no noisy-flat safety is established.

The first prototype's FP32 feature comparisons exposed carrier-angle drift at
zero crossings:4 failed/19 passed. Both original source and log are retained.
Integer FFT-bin phase is reduced modulo its spatial period before conversion
to radians. Existing tolerances are unchanged. All23 new CPU tests and68 related
checks now pass,including independent NumPy coordinates,four CFAs,FP32/FP64,
rectangular/mixed-layout inputs,selection independence,exhausted slots,ADC and
mixed-cell bypass,RNG/frozen mode,strict initialization and nonzero adapter/
matching-fixture gradients. Zero-adapter fixture outputs are bit-exact;actual
CUDA/model-output parity is still pending.

A fixed CPU profile uses the first noisy mesh/photo/mixed/flat training batches
plus protected main-sky and nominal-cab cached inputs. Only RAW/variance/CFA are
interpreted;no target,reference or parent prediction is read. Across18 images,
12 FP32/FP64 feature calls compare85,196,800 FP64 values with independent NumPy.
Largest absolute error is2.25e-12. FP32/FP64 bins agree in all6cases;RMS map
errors1.02e-7..1.75e-7 and maximum2.43e-6. The biggest FP32 feature tensor is80MiB;
peak process RSS1.30GiB. Single CPU feature calls on2cores take.057-.282seconds
for these batches;these are not end-to-end model or CUDA throughput results.
Full feature tensors are not archived;their hashes and selection/power/error
records are preserved.

One existing V172 checkpoint is loaded on CPU. Both raw and EMA strictly
initialize all188 original tensors and one zero adapter tensor. The old module
hashes match V175's original V172 initialization exactly. The new variant has
2,092,026 trainable parameters(default full matching network enabled),plus
124,909 frozen parameters. No optimizer state migration is claimed. The
preparation runs no actual matching,frozen,V143/DINO or sampler forwards,no
updates,new source/sensor draws or RAW decode;CUDA is not initialized. Test-
double forwards and actual checkpoint loading are labeled separately.

All6 native case records,shape/byte counts,188-tensor compatibility x2,source
bindings,18 table cells and links pass publication verification. Both the
failed prototype and current source/test/profile bytes are embedded in the
public receipt. The68 passing checks/profile are completed work,not trained
quality. No new model is promoted and no new restoration/native crop result
is claimed. CUDA parity,real matching gradients/memory,training and full numerical/
native review remain necessary. Existing V172/V174/GFX comparisons remain.

The V175 training PID/create-time and completion watcher are still live;all96
prior neural files and18 sealed helpers are byte-identical. The new97th source
is a separate untrained variant and does not enter the frozen V175 workspace.
No training recipe/checkpoint is changed or restarted. Original photos and
/mnt/dataz are not accessed;both protected scenes/siblings remain excluded.

[Model/preparation report](../docs/phase-evidence-matching.md) ·
[CPU evidence and preserved failure](../docs/results/v178-phase-evidence-preparation-v1.json) ·
[Publication verification](../docs/results/v178-preparation-publication-verification-v1.json).
