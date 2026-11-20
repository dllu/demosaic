# Train directly for weak contrast recovery

Recorded: 2026-11-20T09:26:24-08:00 (America/Los_Angeles).

Completed all four `direct-detail-response-v1` heads on 768 new photos.
Each starts from the earlier learned local gate on frozen Local 50k.
The direct objective uses the delivered 32-pixel-grid blend and a signed
target response. Two arms add covariances on both green Bayer lattices.
The four-arm fit took 23.30 seconds after 457.83 seconds of frozen
forwards and statistics preparation. All 27 focused scene tests passed.

The fresh 48-photo replay was close to the parent response ceiling.
Eight source IDs were shared with the fixed full427 benchmark. We
recaptured the remaining 40 at the established 0.22 contrast with new
noise, unchanged camera geometry and already locked inference policies.
The signed-response EMA gains 0.526 response points, adds 0.030 DN16
flat RMS and adds 0.124 DN16 increment RMS against a calibration limit
of +0.10. At equal response it lowers increment RMS by 0.131 DN16
versus the earlier whole-photo gate on these crops.

Numeric work and native viewing are complete for this component.
The sky stayed pixel-identical and the coarse fence stayed connected.
Transferred cab mesh still has missing crossings. The full-model
427-photo and camera chart continues to cover the evaluated full models.
[Report](../docs/direct-detail-response.md) ·
[Full-model chart](../docs/performance-history.md) ·
[GFX scene review](../docs/gfx-qualitative.md) ·
[Fine green cab mesh review](../docs/gfx-green-mesh.md) ·
[Frozen sources, weights and receipts](../docs/results/direct-detail-response-v1/evidence.tar.xz).
