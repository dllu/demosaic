# Calibrated sensor-noise releases

The current [V117/V118 pair](band-loss-training.md) tests a training loss while
keeping the physical noise recipe fixed. This release check records a separate
possible data improvement; it establishes no new restoration-quality result.
[Pinned author resources and dataset-card receipts](results/PNNP-release-scope-v1.json).

## Available method and resources

[PNNP's author release](https://github.com/fenghansen/PNNP/tree/8704a5e8852da305097618f9b1335630dcfdd889)
identifies the April2026 TPAMI version of its earlier noise-model work. It
separates frame, band and pixel components, with a learned pixel-noise proxy.
Released sensor weights cover **Sony A7S2 and IMX686**. Noise synthesis and
denoiser training are provided; training the proxy itself is omitted. The source
is Apache-2.0; this check does not establish separate archive weight terms.
Calibrating another sensor requires its dark frames. These resources do not
provide measured GFX100S, GFX50R, Q2 or a7R II noise calibration.

The [AIM2025 RAW-denoising report](https://arxiv.org/html/2510.06601v1#S5.SS3)
describes a hybrid of modeled noise and measured dark-frame residuals, including
a low-SNR detail/noise tradeoff. Its results concern calibrated RAW denoising;
they do not rank our joint RGB restoration or prove a benefit on these cameras.

## Data scope and next quality decision

Both author cards, [LRID](https://huggingface.co/datasets/hansen97/LRID) and
[LRID simplified](https://huggingface.co/datasets/hansen97/LRID_simplified),
declare **CC BY-NC4.0**. They are excluded from training under this project's
requirement that new data permit commercial use. Only small release/license/card
metadata was fetched; no dataset images or model weights were downloaded.

Our inference: measured read-noise components are worth investigating if dark
regions remain weak after the current objective comparison. A new camera's
calibration must come from actual evidence; another sensor's released profile
does not establish it. The existing [GFX input-conditioning check](noise-conditioning.md)
and [stabilized-noise diagnosis](stabilized-noise-proxy.md) retain their scopes.
Current data, noise settings, model choices and original jobs stay unchanged.
