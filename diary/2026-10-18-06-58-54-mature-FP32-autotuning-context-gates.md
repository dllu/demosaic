# Mature V43/V63 autotuning context gates pass

The corrected offline-cache experiment completed four serial fresh-process
probes on the mature references. Original/autotuned medians are1481.427/
926.416ms for V43 and1416.573/865.949ms for V63 on the fixed four512px
GFX contexts. Three warmups, five unhooked samples, one trace, B4 channels-last
IEEE FP32 and16GiB allocator cap. No whole-frame speed or training gain inferred.

Every6,291,456 camera-RGB value passes original1DN16 max/.25DN16 RMS bounds
per context. Independent float64 maximum/math.fsum RMS replay agrees within
1e−15 DN. Maximum errors.058593/.062499DN; worst context RMS.000994/.000916DN.
No thresholds changed. Model/actual-backbone/checkpoint/RNG identity and
repeated/traced byte equality, including signed zero, pass. All four actual
CUDA traces map every event via CPU ID/runtime correlation/thread containment.

Rendered and actually viewed all16 native triplets/24 unchanged160px cells
for sky/building/foliage/fence. No visible policy difference; mature outputs are
clean but foliage remains soft. Same input/Malvar and independent ISO100
reference across methods, same WB/matrix/+2EV display. Context outputs are
distinct from full-frame restores; separate ISO100 is not GT.

The [report](../docs/mature-cudnn-autotune.md) and
[registry](../docs/results/mature-cudnn-autotune-v2.json) preserve full source,
checkpoint/backbone/output hashes, all gates/traces and actual native view.
Private/public publication SHA256:
`47ad698a66d959dc23b4af86d2f0187cd353d5b56ab6ff3c9ad04ec5a372f16e`.
Private root:`/mnt/external/demosaic/benchmarks/mature-cudnn-autotune-v2/`.

The preserved v1 failure occurred before a forward because a frozen-CWD
environment setup chose an incomplete HF cache. v2 requires repository HF_HOME
and hashes the existing pinned ViT-S/16/ConvNeXt-tiny config/weight files.
No download, model/precision change, or gate relaxation. All corrected workers
and controller exited. No production/default change, training extension or
promotion. Next full-frame mature-reference validation requires reserved
space; keep all existing evidence and the original project objective intact.
