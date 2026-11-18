# Reviewed the first localized whole-scene endpoint

Recorded: 2026-11-18T12:15:22-08:00 (America/Los_Angeles).

The localized spatial arm finished 2,400 updates in 1,725.31
seconds. The verified checkpoint SHA256 is
`9f3a5cc187d0b9c9cd8de5bb22bf93bf29d0e8d0f67a474fbc834c71727eb789`.
Its unmodified training receipts record all 4,800 distinct photos
and 19,200 crops, with 2,386 localized scenes. Plain local training
started after the controller audit.

The same 32 groups from the eight-photo pilot were evaluated with
EMA weights. Coupled ISO6400 flat-core RMS is 4.85 DN16, down
from 5.22 DN16 for the older spatial EMA and above the 100k parent's
4.21 DN16. Pooled fine response remains slightly lower. All three
held-out boards and triplets were checked. The eight standing real
boards were also inspected at native size. Sky stays smooth and the
coarse lattice remains coherent. Fine cab crossings are incomplete
under both conditioning profiles, with stronger diagonals under
transferred conditioning.

The first endpoint's scoped numeric and standing native reviews are
complete. Evaluation on the full64 held-out panel and the three
fixed broad panels awaits the other three trained checkpoints.
[Report](../docs/scene-local-contrast-2400.md) ·
[PSNR history](../docs/performance-history.md) ·
[Main GFX review](../docs/gfx-qualitative.md) ·
[Fine cab review](../docs/gfx-green-mesh.md).
