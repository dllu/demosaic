# Where the Bayer phase correction lands

Recorded: 2026-11-19T02:51:43-08:00 (America/Los_Angeles).

Tested regional modulation of the frozen conditional mixture
using four overlapping 20-pixel footprints inside its 32-pixel
Fourier window. The registered variant has effectively the
same ISO6400 intact response as a strength-matched conditional
control and raises absolute gap error by 0.25 DN16. Both
standing scenes and three native exact-target comparisons
were viewed. The sky stays smooth and real fine junctions
stay incomplete.

Directional projection changes how to read the previous gap
results. In the 12 ISO6400 weak-wire gaps, 65.02% of the
conditional correction energy belongs to the continuing
strong wire and 0.13% falls in the planted weak family.
Removing the strong-band correction raises absolute gap
RMS from 148.22 to 154.06 DN16. Retaining just that band in
the exact gap gives 145.86 DN16. Those last two are score-only
controls with construction geometry. The rendered methods
use only the observed Bayer and frozen models.
[Report and triplets](../docs/local-phase-envelope.md) ·
[Main scene map](../docs/gfx-qualitative.md) ·
[Fine cab map](../docs/gfx-green-mesh.md).

The scoped numerical and native reviews are complete. The
crop diagnostic has no 427-photo or measured-camera PSNR result.
[Comparable PSNR history](../docs/performance-history.md).

The larger-corpus local arm verifies 26,500 updates on 53,000
distinct photos. Matched training remains verified through 25k.
The 64-photo numerical review and actual exact-target crop
viewing are complete at 25k. Independent ISO6400 flat error
falls about 0.10 DN16 and response falls 0.20–0.25 points
relative to 20k. Both standing scenes are running at 25k.
[Training audit](../docs/scene-full-epoch.md#execution-status) ·
[25k photo review](../docs/scene-full-epoch-25k.md) ·
[Full 25k review launch](../docs/results/scene-full-epoch-v1/queue-full-025000-launch.json).
