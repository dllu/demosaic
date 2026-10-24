# Complete eight-view GFX RGB16 native review

Recorded: 2026-10-24T05:02:06-07:00 (America/Los_Angeles).

Previous turn classified as progress: the V112 Small initializer, native
comparisons and matched V114/V115 CPU checks/queue were committed and pushed.
Revalidated the original evaluation controller4127938/1792825828.32 and its
running photo child675804/1792839411.4, audit owner4138085/1792826759.29, and
new continuation controller726126/1792842066.86. All identities match live
processes. The continuation controller is waiting with no children; it correctly
does not overlap the original CUDA chain. At the later photo log check, 2,000
averaged batches were retained and 284/443 sources had completed all conditions.

Reviewed the already completed V104 eight-view full GFX export without new
inference or RAW decoding. Original full-frame result SHA
`d7ccee897a19976fa297702106db91de58ae5e6a30db260d1792f2566127a271`;
inference receipt SHA
`992f58d7c9db8142d3cb3d71cdceb1badfdf33ee66493702cbc0afc0e075e6dc`.
The completed owner3963376 is absent. Both TIFFs are full8746×11662×3 uint16,
with explicit16-bit and color-space tags. Rechecked original file hashes:

- Camera RGB16: `7744b2afc8fa5b1ad23df6a5dfde015f0ac96d7b872d1921ceea1c18d89069c0`.
- sRGB16: `5701b93d95747f77fca7b363641a9e1e20474ed6e414d35613985b92f94fb306`.

Sampled33 full-width rows of both files. The1,152,084 channels at unclipped
camera pixels fall within independent camera-RGB16→sRGB16 quantization
intervals;2,454 channels at clipped camera pixels are excluded. The declared
camera quantization allowance is .505DN16, plus1e-6 linear-render arithmetic
allowance and .501DN16 final sRGB rounding. This checks encoded-file consistency;
no original full FP32 prediction survives, so it is not a learned-precision or
full-image FP32 quantization proof. The actual CLI sRGB16 preview uses exposure×1;
the native comparison uses common +2EV decoded from camera-RGB16.

Rendered all four restored methods from their actual camera-RGB16 exports,
giving V104 single/eight-view, V112 and RawNIND pre-upsampled identical
clipping/rounding history. Shared noisy/reference arrays are retained floats;
all methods use identical NumPy64 WB/matrix/sRGB transforms and unchanged native
160-pixel sensor ROIs. All36 cells across three boards were actually viewed.
Independent Torch64 rendering reproduces all24 restored PNG cells bit-exactly.
Six noisy/eight-view/separate-ISO100 triplets read back exactly to their viewed
cells. Published metadata clarifies RGB16-derived preview encoding; original
generic triplet receipts remain byte-preserved and linked.

Single/eight-view V104 changes remain small in full-frame sky/building/foliage;
fine foliage and saturated-sign detail stay soft. The learned variants retain
thinner, more continuous fence strands than pre-upsampled RawNIND. No broad
superiority claim or pixelwise GFX scoring. DSCF3880 ISO100 f/5.6 remains an
independent qualitative reference to DSCF3879 ISO6400 f/1.7, not GT.

The original timing records885.93318s tiled inference/blending and890.54888s
CLI measured end-to-end, FP32/tile512/overlap64/B4,520 tiles/eight views each,
peak CUDA allocation10.34284GB. This is a completed-run observation, not a
controlled cross-method timing comparison. The100MP/10s and broad qualitative
superiority goals remain open. V112 stays selected; full eight-view quality
panels and their audit remain in progress.

Updated current guides, README and research status. Also corrected a stale
research paragraph that attached V104's36.80085dB to the newer V112 heading;
the current value is36.90238dB, with measured camera/color gains. The completed
loss-scale execution/material/full-frame text now reports completed evidence
instead of obsolete queued states. Original machine receipts are unchanged.

Sources, preserved actual inference and new review evidence:
`.cache/current-quality-20261023-v1/V104-eight-view-fullframe-review-v1/`.
Public [full-frame review](../docs/dihedral-fullframe.md) and
[receipt](../docs/results/v104-dihedral8-fullframe-review-v1.json).

Validation: both new executed review/publication scripts pass Ruff; public
asset hashes, JSON, local links, native counts and unchanged V112 selector pass.
All seven frozen evaluation/audit/continuation plans retain valid source/input
hashes. Final process inspection confirms all original owners remain live and
the new continuation controller still has no child. No learned work repeated.

