# Measure weak-wire sensitivity to pre-Bayer blur

Recorded: 2026-11-19T23:51:19-08:00 (America/Los_Angeles).

Replayed V120, Corpus 100k, Local 50k and both 1,024-update wire EMAs
on the same 32 held-out off-grid backgrounds with two pre-Bayer blur
widths. All zero-blur inputs regenerated exactly. A zero-blur inference
spot check matched the archive for every checkpoint.

With shared photon counts and read noise, Local 50k recovered 22.44%,
18.99% and 14.59% of the original sharp weak signal at σ 0, 0.55 and
0.85 native pixels. The mild and stronger blur also reduced recovery
as a fraction of the available clean signal. Regional supervision
still lowered continuing-strand error at both widths and delivered
less weak-strand response than whole-core supervision. Viewed two
native crop triplets at each dose. Faint crossings remained incomplete.

The optical widths are synthetic and no training was performed. A
matched optical variation study should retain sharp examples and
measure weak-response, true-gap and flat behavior at a held-out dose.

[Report](../docs/sensor-optical-transfer.md) ·
[Evidence](../docs/results/sensor-optical-transfer-v1/publication.json) ·
[PSNR history and scope](../docs/performance-history.md) ·
[Main GFX comparison](../docs/gfx-qualitative.md) ·
[Fine cab mesh comparison](../docs/gfx-green-mesh.md).
