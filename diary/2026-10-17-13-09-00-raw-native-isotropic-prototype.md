# RAW-native isotropic prototype and genuine GPU engineering checks

Added an opt-in `packed-isotropic` backbone after closing the original4k
normalization study. No quality model was promoted. The standing V43 README
triplets and cached DSCF3879/DSCF3880 qualitative reference remain in place.
The PROMPT objective is still unmet: SOTA and decisive real-photo superiority
over RawNIND are unproven, and no100MP<10s restoration has been demonstrated.

Read the actual RAW-kernel implementation before choosing the new design. It
already sends centered differences from every input CFA color into every RGB
output. An initial hypothesis that it lacked cross-color reconstruction was
wrong, and was corrected in commentary before implementation. The existing
head's324 coefficients/native pixel and native pretrained RGB trunk motivate
testing a different computational layout instead.

Reviewed primary JD3Net methods (§3.1, arXiv2601.00703v2): downsampled isotropic
simplified NAF blocks and learned upsampling. Existing research records already
identify its repository's missing model license/weights. No upstream code or
weights were copied. The prototype uses our existing GatedBlock, lossless
pixel-unshuffle of packed physical camera features, six groups of eight
width96 blocks at native quarter resolution, a width32 half-resolution detail
path, FP32 stems/physical skip/tail, and a genuine frozen DINOv3 ConvNeXt
four-stage pyramid at quarter resolution. Entry coordinates use RAW/log
variance/phase/WB/matrix directly without per-image extrema or GAT. Learned
output remains unrestricted camera RGB; retaining input samples does not prove
texture recovery or color accuracy.

Prepared V70(DINO)/V71(no-DINO) fresh matched recipes: common seed51,
original40000 schedule/LR2e-4/warmup500, first2000 review via explicit stop,
B16/native256, frozen Commons40170/native128captures106groups/paired32,
wide8 palette and existing4×→geometry/PSF→area2 pipeline. Prior pretrained RGB
models are external quality references, not matched fresh-training controls.
Neither quality arm is launched. No protected-final model scoring or new
training-source admission occurred.

Validation:117 focused CPU tests passed in65.55s, including local and new
backbone uninterrupted versus interrupted/restarted training, zero DINO branch
common initialization/RNG/gradient preservation, all four CFA patterns,
one-code16-bit input preservation, odd rectangles, native-grid padding/cropping,
portable nonzero context reload, frozen-backbone gradients and legacy RGB/
RAW-kernel checks. Ruff and git whitespace checks passed.

`scripts/preflight_packed_isotropic.py` completed12 discarded production-size
B16/native256/BF16 updates with genuine pinned DINO and actual Commons/native/
paired data, including production4/2/2 spawned workers. All863 trainable
tensors received finite nonzero gradients and changed;3,686,156 trainable
parameters, model/EMA/Adam stayed finite. Frozen DINO stayed bitwise unchanged
and gradient-free. Every portable model/backbone tensor and two fixed-photo
predictions were exact in FP32/BF16/FP16 after EMA reload. Peak training CUDA
allocation11.584GB; this is not total UMA use. No training extension or quality
score is inferred from these12 updates.

Full/public receipt SHA5833658a26f4e1659431415fbd8235da67f9a753483e6ea92bd85b8837bd56cd,
at `docs/results/packed-isotropic-CUDA-preflight-v1.json` and
`/mnt/external/demosaic/benchmarks/packed-isotropic-CUDA-preflight-v1/receipt.json`.
Discarded checkpoint SHA25553cbb8001963b018acd5d8480565e20e8c5cfc9f146dd216bfee66389d787;
producer source bundle50dc11ec5c906fbbc4d3c5b1b530b95acb3b40a5f725d3a622891b2471c21d16.

The small eager body was not immediately fast: synthetic B4/native512 forward
medians276.94ms FP16/279.14ms BF16. A separate discarded block-compilation
experiment cut median FP16 time276.58→148.03ms (46.5% less), largest observed
timed-batch RGB difference1.1921e-7. Only groups/local blocks/decoder were
compiled; DINO and physical work stayed eager. Two fixed photos ran finite,
but their eager differences were not measured. Random timing input was neither
seeded nor retained; this is engineering timing, not quality or trained-model
precision evidence. No decode/transfer/blending/write or full100MP timing,
and no CLI/default compile policy change. Receipt SHA
1a02056c4266dc83148c8ccb23b495cffc0e99774d16eeab4e46d31a76503c29,
public `docs/results/packed-isotropic-block-compilation-v1.json`; exact operator
archived beside the private receipt. Both preflight/profiling owners exited0.

Started the actual selected-domain training batch sweep for this architecture:
B4/8/16/32, two shuffled repeats,15 warmup+45 measured updates. It uses the
discarded12-update EMA only as a shared timing initializer, fresh AdamW and
the benchmark's common planned5000 schedule. It never initializes a quality
run. Controller PID931411 (identity in its `controller.json`), tool session72485;
root `/mnt/external/demosaic/benchmarks/packed-isotropic-training-batch-sweep-v1`,
log `.cache/packed-isotropic-training-batch-sweep-v1.log`. Results are pending;
no batch/LR choice changes. Do not launch overlapping owned GPU work. Finish
the sweep, verify runtime source/manifests/initializer and domain counts,
then assess a matched fresh-training quality run and native review. The
Commons background downloader remains separate; no duplicate download started.
