# Closer GFX pair and texture crops

User requested DSCF3879/DSCF3880 going forward and added foliage/fence views.
Cached the two requested 2023 RAFs, verified SHA-256 against read-only sources
and unchanged source metadata. They are ISO6400 f/1.7 1/240s at17:13:27 and
ISO100 f/5.6 3s at17:17:05: 3m38s apart, almost identical framing, still not GT.
Scene and siblings remain evaluation-only. No source files were modified.

Selected four fixed160px ROIs using input/reference images only. Kept sky and
building; added ivy foliage and chain-link mesh. Input/reference green
correlation over512px contexts selected integer reference shifts0–1px, with
no warping/resizing or per-panel brightness. Selection is in the standing
config and AGENTS.md now explicitly names the new pair and four regions.

Ran V16 step5000 and RawNIND on the complete101.996MP noisy frame before
cropping; default FP32 correction and FP16 base for V16, IEEEFP32 RawNIND.
Full outputs and archived source/weights:
`/mnt/external/demosaic/evaluation/gfx-3879-3880-v16-5k-full/`.
Shared-machine restoration36.39s/19.88s, excluding decode/load/render/encoding;
not an idle benchmark. Both quality and10sec goals remain open.

Published eight512x192 PNG triplets (three native160x160 panels each), complete
receipt and detailed doc. README now shows new-pair foliage/fence. Historical
old-pair receipts/images remain unchanged. Checked exact noisy/reference pixel
identity across methods, all PNG dimensions/hashes and all four TIFFs as
8746x11662x3 uint16 with16bit sample tags (sRGB ICC profiles present).
Visually reviewed new texture crops and sky/building. Detail loss remains,
including mesh smearing and V16 foliage desaturation. Aperture differences
contribute to reference sharpness, so no pixelwise quality scores are assigned.
