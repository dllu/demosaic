# V84/V85: matched private-native data comparison

This is the protocol for the completed V84/V85 comparison. **V84 is now the
preferred development baseline**; see [current model choices](current-model.md)
and [the completed results](native-data-original20k-review.md). The eligibility
gates below describe that particular study, not requirements for updating the
README or selecting a stronger architectural baseline.

The completed bank-gradient study did not improve camera or weak-detail
requirements. This separate study tests the already reviewed private-native
extension, preserving the mature V63/DINO architecture. The only treatment
difference is the native training manifest: **128 captures/106 groups versus
150 captures/120 groups**. The extension adds 22 approved low-ISO GFX100S
captures and 14 additional group labels; nine rejected captures remain excluded.
[Admission and unchanged-legacy evidence](personal-native-quarantine.md).

Both arms start freshly from genuine V63 original20k EMA, SHA-256
`ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5`.
Neither starts from the closed V78–V83 heads. Original budgets are **20,000
updates per arm**, B16/native256/BF16/channels-last, seed53, deterministic
execution, maximum LR1e-5, warmup200 and the original20k cosine horizon.
Initialize fresh optimizer/EMA/RNG. The frozen official DINOv3 ConvNeXt-Tiny,
RGB trunk, physical anchors and variance stabilization remain identical; no
directional, bank, kernel or new adapter branch is added.

Both use cleaned84,867 Commons and paired32, .25 native/.25 paired fractions,
sensor-valid camera supervision, the unchanged Charbonnier loss and existing
exposure/noise/flat-palette draws. Geometry/PSF precede final area2 reduction.
Domain selection precedes loading. The new Commons arrivals remain outside
both arms. Shared Commons/paired sampled observations must match exactly;
native observations may change with membership. Require identical initial
EMA/DINO, every logged domain/LR and final Python/CPU/CUDA RNG states. One
matched training seed does not measure training-seed uncertainty or convergence.

Private rows retain their pinned permission, provenance, grouping and cache
identities. Source images, capture/travel metadata and private overviews stay
outside Git. Targets are low-noise phase-bin estimates, not exact noiseless GT.
Standing GFX3879/3880, its siblings, other qualitative scenes and protected
development/final sources stay excluded from training. The existing admission
screens are finite heuristics and do not establish complete scene independence.

Run serially after the exact cache-preparation owner exits successfully, with
48 GiB available RAM for 60 continuous seconds before each arm. Preserve the
24 GiB CUDA cap, 24 GB training-memory stop,128 GiB root/500 GiB external launch
reserves and a 36,000-second active timeout per arm. A failed guard stops the
new study with saved state; no automatic retry, horizon extension or checkpoint
selection. Retain engineering1k/4k/10k/final snapshots; evaluate the final20k EMAs.
CPU mixed-domain preflight and genuine B16/native256 CUDA checks precede any
quality training. Short probes are discarded engineering checks.

Fresh FP32 review must include both final EMAs and V63 on all427 photographs,
seven conditions/four CFAs, procedural16, known-four/unseen-five measured-CFA
panels,418/416 source sensitivities, all24 carrier/four flat configurations,
all hue groups and cached GFX/highlight regions. Preserve canonical camera-linear
and highlight failures with the target-convention caveat. Compare V43 and both
RawNIND calibrations under unchanged source/protocol witnesses. Never score the
independent ISO100/AHD RGB as exact pixelwise GT. No protected-final scoring yet.

A trained data benefit requires a positive matched photographic PSNR 95% source
interval and known/unseen mean losses no greater than .03dB each. Eligibility
for a later full-frame review additionally requires each arm's photo, known and
unseen means to improve by at least .05dB over fresh V63, each with positive
source/scene-bootstrap95% lower bounds; photo SSIM may lose at most .0001.
Native review must show no new color, detail or highlight failure. These
bootstrap intervals do not represent training-seed uncertainty. A claim of
weak-detail recovery also retains the earlier descriptive +.05 matched signed
gain requirements in both high-noise cases, flat RMS≤1.25×control, and no ADC
gain loss exceeding .05 in any declared case. Report every group, including
adverse groups. Failed criteria close this study at its original20k budget.

Every performance report includes at least two native160px noisy/restored/exact
synthetic-GT triplets per checkpoint, with identical source/ROI/display/noise
settings, checkpoint SHA and source attribution. View GFX sky, building,
foliage, chain-link fence and illuminated sign/platform crops at native scale;
ISO100 remains an independent reference with aperture/exposure/motion caveats.
Keep current documentation and image comparisons updated when useful versions
are available. Checkpoint-specific full-frame claims need their own complete
101.996MP linear/sRGB16 export, quantizer,
native-quality and cold/warm timing checks. This experiment alone cannot prove
SOTA, broad real superiority or100MP/10s.
