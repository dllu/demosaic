# Cab mesh fundamentals fit the current spectral band

Recorded: 2026-11-07T09:02:43-08:00 (America/Los_Angeles).

Checked a concrete architectural hypothesis while the original V165 worker
continues: does the radial frequency cutoff exclude the fine cab mesh itself?
The two existing fixed160×160 cab windows are analyzed in both cached ISO100
camera JPEG and independently demosaiced AHD camera-green references. No crop
pixels are resized and no original RAF or `/mnt/dataz` is read.

After affine detrending and a Hann window, the strongest peaks in each diagonal
frequency-sign family lie at packed radial frequencies0.213–0.281. All eight
strongest family/window/reference cases have nominal smooth-band gain1 under
the current1/32..0.45 radial band. Several higher harmonics fall outside the
upper limit. The dominant fundamentals therefore do not look excluded by the
band itself. This weakens a simple cutoff-only explanation for their loss.

This is a nominal polyphase-frequency mapping, not the actual learned transfer:
it omits overlapping256-frame taper, phase mixing, spatial support, Malvar
reconstruction and the unrestricted direct RGB path. It cannot rule out benefits
from a wider band or identify a trained-path cause. JPEG powers and AHD camera
green powers are not comparable measurements. Aperture, exposure, motion,
rendering and coordinates differ; these remain qualitative references, not
exact GT, noisy-input confidence or model-quality scores.

[All fixed peaks, coordinates, exact cached bindings and executable source](../docs/results/mesh-band-coverage-20261107-v1.json).
The V165 recipe is unchanged. No neural forward, sensor-noise draw or new
training-source construction was performed for this diagnostic.
