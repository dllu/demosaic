# Fixed mature-model mixed-precision pilot

The current mature V43/V63 full-frame results are IEEE FP32:118.22/120.48s
after warmup with bounded cuDNN search. The older V42 FP16 result uses different
V37 weights and does not qualify these mature checkpoints. This separate
execution study keeps their learned tensors unchanged. It supplies no new
training, model promotion, quality gain or100MP/10s claim.

Compare three explicit policies: original IEEE FP32; ordinary CUDA FP16
autocast with the original first hidden branch; and CUDA FP16 with the existing
first-hidden-stage autocast flag. Original physical projection, final native
skip, output projection and physical inverse remain guarded FP32 in every
policy. The underlying checkpoint/config/default remains unchanged; a scoped
research override restores the hidden flag and ambient settings on every exit.
V43 uses its original DINOv3 ViT-S, V63 its original ConvNeXt-Tiny. Do not claim
they share a foundation checkpoint or infer precision behavior for V92's head.

Before any new CUDA work, require unit tests and a genuine-weight CPU-only
execution preflight for both checkpoints. Explicit CPU FP16 autocast is an
engineering emulation; the production CPU API remains FP32. Check all four
CFAs, ADC/highest-noise inputs and an exact one-DN ADC perturbation on fixed
native64×80 inputs, one frozen encoder pass per forward, FP32 physical head/
tail/output, intended first-encoder dtypes, finite outputs, more than256 native
codes and a nonzero one-DN response. Require exact explicit-FP32 identity with
the hidden flag enabled, exact repeated CPU outputs, unchanged state/parameter
identities/config/checkpoint/input bytes and Python/Torch RNG. No CPU latency
or small synthetic accuracy result establishes CUDA performance or photo quality.

Any later CUDA pilot must wait for successful completion and actual exits of
the V92 training, ten-stage review, CPU closure, retained-reference and native
package jobs. Preserve all their evidence and do not overlap another owned
GPU job. Freeze new sources and inputs before launch, use local SSD outputs,
48GiB RAM headroom for60s,24GiB active RAM floor, root64GiB/external500GiB
reserves and a16GiB CUDA allocator cap. Bound its single worker to900s with
no automatic retry, full-frame continuation, training or default change.

The fixed CUDA screen should reuse the existing two native256 exact-GT photo
observations, the four B4/native512 standing GFX contexts, and all96 unique
analytic component observations:48 ADC carriers plus32 noisy carriers and16
flat observations. Preserve all12 ADC groups and every CFA/draw; ADC duplicate
draw labels are not independent observations. Add a native ramp/one-DN probe
at all four CFAs. Every policy uses the same complete measurements, fixed
camera/noise/display transforms and learned weights. No target enters the
model forward. Save full unquantized outputs and dtype/state/RNG evidence.

Render the same native160px crops and actually inspect them before reading
new quality/timing summaries. Include two noisy/restored/exact-GT photo
triplets per model/policy and sky/building/foliage/fence GFX comparisons. The
separate ISO100 rendering is a qualitative reference, not GT. Report sources,
ROIs, checkpoint hashes, noise and exposure; never resize crop pixels.

This is a finite screen, not full quality qualification. Require finite
FP32 physical outputs, native ramp codes/one-DN response, no visible new
artifact, photo PSNR loss at most.05dB and SSIM loss at most.0001 on each of the
two fixed photos, no individual ADC signed-gain loss greater than.05 versus
that model's FP32 output, weak-carrier loss at most.05 and flat-luma RMS at
most1.25×FP32. Record physical maximum/RMS differences without calling FP16
bitwise equivalent or relaxing the earlier FP32 autotuning1/.25DN16 gates;
these are different numerical interventions. Do not turn a pilot pass into
a population-quality or SOTA conclusion.

For the four actual512px GFX contexts only, use three excluded warmups and
four synchronized samples per policy in balanced forward/reverse order.
Report first-call/search cost separately, bounded search limit10 for all
policies, unchanged allocator quota and restored backend settings. Resident
timing excludes full-frame tiling/blending/export. A descriptive median gain
of at least5% on both models can justify a separately frozen full quality and
full-frame study only after the native/numerical screen. Ranges are not
training-repeat or timing confidence intervals. The original10s requirement
still needs an actual complete100MP16-bit result.
