# Whole-photo patch covariance for weak detail

Recorded: 2026-11-19T18:04:50-08:00 (America/Los_Angeles).

Estimated inter-frequency covariance from disjoint, visually similar
patches in the same photo. The filter uses the query's own signed
Bayer innovation. On 24 separate ISO6400 photos, confirming both green
grids adds 0.180 fine-response points with 0.092 DN16 higher increment
error and 0.176 DN16 higher exact-flat error. The confirmed diagonal
recovers more response with slightly lower increment error. Calibrating
on independent noisy pairs selects zero strength at both noise levels.
[Report and frozen evidence](../docs/scene-patch-covariance.md).

Viewed the Lilacfork and Saint Nicholas Cathedral triplets and both
exact-flat controls. Both GFX100S pairs were reviewed with the
established exposures, noise profiles and references. The sky looks
smooth. The coarse fence remains coherent and the cab crossings are
still incomplete. The published camera boards bind the verified
Corpus 100k EMA predictions. [Main scene](../docs/gfx-qualitative.md) ·
[Fine green mesh](../docs/gfx-green-mesh.md).

Completed numerical and native review for the frozen-weight component.
Fixed-panel PSNR is recorded separately. [Performance history](../docs/performance-history.md).
