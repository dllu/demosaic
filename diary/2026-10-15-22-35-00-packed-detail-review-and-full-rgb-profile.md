# Packed detail review complete; retained RGB model profiled

The frozen V40/V41 workflow completed at 2026-10-16 05:32:31 UTC. Both stopped
after1000 updates and all41 logged domain/observation hashes match V38. Source
bundle is `89cf3175165fe16025295b7102fa7b0bc255eea9cf3fc69c4bdd33fd94933e03`.
V40 checkpoint SHA is
`f5e4efd3d11e86e87e8204dfd27a21d8560f64d6e44f20df13911fad71e27ff3`;
V41 is `aeab8f88fc24eda4897c5922a9b788fade491e891f3a8a5a9943aac6cd89728f`.

The Wiener detail prior recovers much of V38's real-camera noise loss but still
fails against the full-resolution V37 control. Known primary PSNR is
52.90480/52.85833dB for V40/V41 versus54.27943; unseen52.22122/52.23809 versus
53.67990. V40/V41 full427 photo PSNR is31.85320/31.82236 versus34.65497.
V37 minus V40 is+2.80177dB with source interval[+2.72241,+2.87797]. Phase LR10
does not close the gap. Both new variants remain experimental and stopped;
README retains V34 as its representative model, with a link to this review.

`docs/packed-detail-v40-v41-review.md` and its receipt publish20 verified native
triplets, including two exact synthetic GT triplets per model and GFX foliage/
fence. Noisy/reference panels match cached V37 exactly; all source/ROI/noise/
display identities and checkpoint hashes are retained. The real AHD/ISO100
references are labeled accurately. Reuse requires identical protocol and exact
24/30 real classical pair summaries and37,212 synthetic classical rows. Four
new complete8746×11662 RGB16 files passed full SHA/size, shape/dtype/bit-depth,
sampled codes and sRGB ICC checks. GFX restoration took18.82/17.89s, successive
shared-machine runs, not a repeated idle benchmark. Fine residual grain remains.

After the controller finished, a read-only resident-tile probe profiled retained
V37 EMA, same GFX input-only prior, four native512 tiles. Five forwards after
three warmups have median187.89ms CUDA, range186.89–188.46ms. Three instrumented
forwards match original output bit-for-bit. About78% of device time belongs to
the RGB CNN,9% to DINO context. CPU annotation and corresponding GPU annotation
rows are duplicated in this PyTorch profiler; the receipt selects CPU ranges
once and does not sum nested operator/kernel rows. Host MHC time includes
waiting on earlier GPU work and is not its device execution cost.

The first encoder's FP32 residual skips repeatedly promote native activations,
causing recasts for FP16 convolutions. The next concrete speed experiment is to
keep the separate FP32 physical head/final skip but test FP16 hidden activations
in that first stage. This is a numerical change requiring ADC/weak-detail tests
and matched complete quality/native-crop review. It has not been implemented
or adopted; current quality comes first. See
`docs/full-rgb-inference-profile.md`; executed workflow/trace/table/raw receipt
are archived under `/mnt/external/demosaic/benchmarks/full-rgb-inference-profile-v1/`.

All321 tests passed on final source in41.82s and Ruff passed. No owned training
or quality-evaluation job remains active. Commons download PID3989567 continues
under its existing lock, with over10,000 new files/~42GiB this session. Frozen
experiments do not automatically admit newly downloaded data. Broad superiority,
current-architecture trained DINO ablation, protected-final assessment and the
10-second100MP goal remain unproven.
