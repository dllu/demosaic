# V104 unseen-camera spatial regressions and fixed stress crops

Recorded: 2026-10-23T17:42:38-07:00 (America/Los_Angeles).

Examined the two largest mean-decreasing unseen development scenes, Coulicoco
and top_of_Expedit. Both are Canon EOS M100/ISO12800. For each, selected the
worst V104-minus-V102 measured-CFA PSNR tile from the existing complete 90-crop
panel, then replayed its original batch partners on CPU IEEE FP32. Two real
DINO-backed forwards per model plus two RawNIND:CFA-channel batch forwards;
all 91 EMA tensors and official frozen Tiny identities verified. Weights,
configurations, parameter IDs, inputs and per-forward RNG remain unchanged.

Selected full448 CFA scores V102/V104/RawNIND are57.82471/56.98928/58.92127dB
for Coulicoco and61.15482/60.67192/62.08642 for top_of_Expedit. Original CUDA
V104-minus-V102 changes are−.83543/−.48289dB. All12 replay rows, including
batch partners, match original primary/auxiliary PSNR within 7.63e-6dB.
Independent NumPy64 masked-CFA scores reproduce within the bound in the audit.
Measured channel-mean components account for 14.8%/14.4% of V104's full-crop
MSE; most residual error remains after those means. This is an error
decomposition, not an identified training cause.

The native 160 window maximizes signed CFA squared-error increase per valid
sample inside the original448 interior. Viewed 10 cells at original display
and 10 under a shared+2EV shadow display. There are only two physical ROIs.
V104 has more coarse brown-field variation, while RawNIND is smoother and
scores better on these specifically selected cases. The independently
processed AHD reference retains noise and is not exact RGB GT. Display boosts
alter no predictions or scores, and all methods share coordinates/transforms.

Published 12 triplets with source,ROI,checkpoint,noise/display metadata and a
fixed development stress catalogue in configs/paired-adverse-v104.json. These
remain outside training and do not change the current baseline, active
training/evaluation plans, promotion criteria or protected 16-scene reserve.
[Current camera report](../docs/real-camera-quality.md#targeted-dark-field-regressions) ·
[Replay, independent audit and native review](../docs/results/v104-unseen-adverse-review-v1.json).

Preserved the first failed worker, which called set_noise on RawNIND (that
adapter has no such method), and its partial outputs. Corrected v2 conditions
only models exposing the setter. A closure initially assumed 9 instead of 12
score rows from the actual partner batches and stopped before publication;
the corrected closure checks recorded coverage. Successful replay/audit bytes
are unchanged. No failed output was published or selected.
