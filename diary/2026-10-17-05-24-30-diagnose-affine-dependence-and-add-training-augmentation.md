# Diagnose learned affine dependence and implement a training-only augmentation

Previous goal turn was progress: pushed7f7ea17 closed and rejected the complete
flat-moment CPU screen. Verified the actual original training/review/download
owners before further work; no duplicate GPU job, restart or retiming.

The physical affine round trip was already accurate. A new fixed CPU experiment
isolates learned coordinate dependence on two saved exact-target photographs,
two selected noisy colors and all four standing GFX contexts. Hold RAW, shape,
CFA/noise, WB/matrix, DINO preview and weights fixed; calculate the same original
affine rule on the central half canvas instead. Rebuild measured coordinates,
noise and physical anchors coherently. Sixteen genuine V60 CPU-FP32 forwards;
fresh baselines all equal retained arrays bitwise; model/DINO/RNG unchanged.
Fabric red mean shifts−.01130 and full border8 PSNR33.03371→30.92785 despite only
modest affine changes. Building changes little; GFX ROI RMS changes range
.0000161–.000394. Uniform orange/magenta can improve while fabric worsens.
Central statistics are not an inference repair or established cause of soft real
detail; up to.1221% of full-context feature samples leave normalized[0,1].

Independently audit40 camera-delta scalars,48 affine scalars and16 PSNR values;
maximum differences9.02e−16,2.43e−12 and .0000107dB. NumPy64 GAT is independent;
MHC and direct feature-crop checks reuse production code. Actually opened all16
native triplets. Eight unchanged PNGs are public: two photo pairs with exact
simulated GT plus foliage/fence pairs with correctly labeled independent ISO100
AHD references. Same noisy/GT panels and full source/ROI/noise/WB/matrix/display
metadata. Cords remain missing; GFX looks nearly unchanged. No cold RAW decode.

Implemented opt-in normalization_augmentation:center-half-mix-v1. Stateless
SHAKE256 seed/step bits select central-half affine coordinates per image with
probability1/2. RAW/targets/DINO inputs stay fixed; one neural forward. Default
none, inference rejects the explicit training mask, no new persistent weights
or model-config fields. Resume rejects a policy change and logs masks. This is
a training hypothesis, with no claimed learned robustness or quality gain.

Complete CPU suite579passed/9CUDA-skipped in95.83s. Focused first run had40passes
and a restart fixture missing the existing required RGB initializer; fix the
fixture, not the production guard. Corrected restart test and complete suite pass.
Public genuine-parent preflight verifies actual original91-tensor EMA before
optimization, genuine frozen DINO hashes/no gradients, all three actual data
domains, finite91model/91EMA/89Adam states and all89 parameter tensors updated.
Twelve discarded B1/native64/FP32 updates across control/full/resumed. Full4 and
2+2 match model/EMA/Adam/Python/Torch/CUDA RNG/best exactly. All four observation
hashes match policy-off; actual masks select Commons/native/paired and also
exercise a full-statistics Commons update. Default/zero-mask and retained CPU
predictions match bitwise. Fixture source bundledb5fb3ba42827e9db043dbc85f069bb1e5568cdafa872f7340d872852bc6a771.

Independent saved-state/log/source/recipe audit also verifies control vsaugmented
RNG and an ordinary loaded-EMA native256 finite output. First audit stopped on
an incorrect assumption that load_checkpoint selects eval mode; explicitly set
eval in the auditor and rerun it. Preserve the failed log; no production loader
or guard changes. Archive executed sources, corrected auditor and unchanged
supporting helper bytes verified against7f7ea17. No extra optimization rerun.

Original V63 control is live at step13475/20000 at capture, with exact controller,
primary/final review waiters and Commons downloader live. Their frozen source
and recipes remain unchanged. New source does not enter their archive. No new
GPU trial/queue: actual BF16/CUDA and matched-quality work follow the original
long-schedule review. No protected-final scoring, model promotion, SOTA or10s
claim; the full goal remains active. Ruff, whitespace, local links and copied
PNG hashes pass.
