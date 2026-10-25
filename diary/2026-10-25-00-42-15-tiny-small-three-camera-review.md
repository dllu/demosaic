# Review current Tiny and Small on three cached cameras

Recorded: 2026-10-25T00:42:15-07:00 (America/Los_Angeles).

The current-guide cleanup exposed a concrete qualitative gap: the Q2/Sony/GFX50R
gallery still used V102/V104 and the earlier half-resolution RawNIND reference.
A fresh bounded CPU job adds V114 Tiny, V115 fitted Small and the stronger
released pre-upsampled RawNIND to the same three fixed native512 contexts.
Original V104/half-reference outputs are reused; cached measured CFA sites
reconstruct all five physical inputs with exactly the earlier execution hashes.
No RAW/source-drive read, noise generation, training admission or optimizer
update occurs. Hot-pixel repair stays off and all models use single view.

The frozen plan SHA is1903c2948c179198c7441ebc46d7eb2caead405189270ffb0ce787b35c5eac21.
It binds61 implementation/reference files and29 inputs. Owner2175059 /
1792913789.2 completes exactly9 model calls:6 joint-model/encoder calls and3
strong-reference/upstream calls. Its process exits successfully after118.99s;
this concurrent CPU2/nice10 observation supplies no full-frame or speed ranking.
Both91-tensor EMAs match their exact final20k checkpoints. Official Tiny/Small
encoder identities, complete model/config/parameter identities, inputs and
per-forward RNG remain unchanged. CPU guards pass; CUDA remains uninitialized.

Inference result SHA isb201e9f11a06488c47ecc8e9468d4f8638325b8e205939ba89eab7d1b535d7be.
Rendering separately forbids Torch module calls and reuses the retained floats.
All21 contexts are finite FP32;12 old floats and6 V104 triplet PNGs are byte
exact. All72 panels of24 triplets re-render exactly:5,529,600 RGB8 channel
values. Three public camera boards contain36 distinct native160 cells; I viewed
all three original-resolution boards and every cell. No image pixels are resized.
Q2/GFX50R retain display×2(+1EV), Sony×1, with shared WB/matrix and fixed ROIs.

Tiny/Small look close to each other and to V104 in these six low-ISO regions.
Dark Q2 rock detail remains soft; Sony window/joint edges stay soft, including
softness already visible in the input. The joint models preserve finer-looking
concrete variation and thinner joints than either RawNIND variant, which look
coarser/more mottled here. There is no clean capture or pixelwise score; neither
RawNIND restoration is GT. This establishes no large new qualitative gain over
V104 or broad real-camera superiority. V114 remains the general baseline.

Exact filenames/hashes are absent from current90,864-source Commons, native and
corrected-paired manifests. This is an exact-source check on existing development
selections, without claiming complete near-scene independence. Original photos
and earlier receipts/assets retain their bytes.

Independent NumPy64 checks also rebuild all9 post-gain CFA normal equations
for the stronger reference; maximum relative residual is2.28e-7. Publication
checks bind all61 frozen files/29 inputs,55 native asset files,36 unchanged
board cells and127 local links. Model choice and the49-point PSNR history
retain their bytes. [Saved-array/publication verification](../docs/results/cross-camera-v114-v115-publication-v1.json)
adds no Torch import or neural work.

[Updated camera gallery](../docs/cross-camera-qualitative.md) ·
[Complete execution/native receipt](../docs/results/cross-camera-v114-v115-current-v1.json) ·
[Native triplet/board metadata](../docs/images/current-cameras-v114-v115/manifest.json).
README/current-model/real-camera/reference guides now link these current results.
The original V117/V118 training and downstream owners remain unchanged.
