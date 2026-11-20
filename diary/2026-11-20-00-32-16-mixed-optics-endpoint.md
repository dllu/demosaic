# Review the mixed optics endpoint and local Bayer evidence

Recorded: 2026-11-20T00:32:16-08:00 (America/Los_Angeles).

Completed the mixed-optics arm at 1,024 updates and audited all 6,144
observations, both final weights and the optimizer. Training wall time
was 1,472.71 seconds. The fixed exact review and both standing GFX
comparisons use the final CUDA IEEE FP32 EMA. Viewed all 12 real
boards and four fixed triplets. The coarse fence stays connected and
the fine cab crossings remain incomplete.

On 24 fresh sources at σ 0.85, the primary weak-response difference
from sharp regional is −0.030 points [−0.219, +0.167]. Exact-flat RMS
rises 0.677 DN16. Differences in false weak projection and continuing
strand error span zero. Viewed both primary-dose fresh triplets.
The earlier optical replay, its response-matched analysis and the
canonical measures remain in the review queue.

On a separate RAW evidence probe using existing synthetic development
scenes, an exterior-phase detector with supplied frequency, masks
and nuisance geometry rises from 49.2% to 90.2% detection when the
query grows from 32 to 64 pixels at σ 0.85. With strong-only captures
the 64-pixel detector admits 4.4%. A strong planted exterior carrier
supports the phase estimate. Verified the split algebra and all 96
CFA mean groups exactly.

[Endpoint and fresh review](../docs/local-optical-mixture-1024.md) ·
[RAW evidence](../docs/optical-raw-evidence.md) ·
[Main GFX map](../docs/gfx-qualitative.md) ·
[Cab mesh map](../docs/gfx-green-mesh.md) ·
[PSNR history](../docs/performance-history.md).
