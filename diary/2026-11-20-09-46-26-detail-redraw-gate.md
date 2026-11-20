# Test weak-detail losses across independent noise draws

Recorded: 2026-11-20T09:46:26-08:00 (America/Los_Angeles).

Completed three matched gain heads on 512 additional training photos.
All start from the previous signed-response EMA over frozen Local 50k
and see two independent draws of each weak, absent and flat role.
The extra terms penalize off-target error in the mean or half
difference of the paired increments. Frozen forwards and statistics
took 594.26 seconds. The three-arm fit took 16.20 seconds.

On 48 new ISO6400 photos, redraw stability gains 0.986 response points
over Local 50k, lowers flat fine RMS by 0.161 DN16 and stays within the
paired increment cap. At equal response it lowers increment error
0.113 DN16 versus the matched direct loss. The weakest half gains less
contrast than the direct loss, and the planted wires lose response.
The earlier stronger-texture panel exceeds its paired error cap.

All 30 focused scene tests passed. Numerical review and viewing of
both GFX families are complete. The sky looks smooth and the coarse
fence stays connected. Fine cab crossings remain incomplete. The chart
continues to cover comparable evaluations of full-model endpoints.
[Report](../docs/detail-redraw-gate.md) ·
[Full-model history](../docs/performance-history.md) ·
[GFX scene review](../docs/gfx-qualitative.md) ·
[Fine green cab review](../docs/gfx-green-mesh.md) ·
[Frozen heads and receipts](../docs/results/detail-redraw-gate-v1/evidence.tar.xz).
