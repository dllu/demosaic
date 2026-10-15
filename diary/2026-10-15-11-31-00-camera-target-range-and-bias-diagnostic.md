# Camera target range and bias diagnostic

Found and reproduced a broad-WB evaluation error: with red WB=0.7, a neutral
reference white requires camera red=1.42857. Even a perfect prediction scored
only 12.13 dB camera PSNR because only the prediction was sensor-clipped; the
synthetic suite additionally clipped the target before color rendering. Preserve
the reference-white target through WB/matrix conversion, and clip both arrays
for the separately defined camera-sensor PSNR. The regression test now yields
120 dB for both perfect camera/rendered predictions. Historical default WB and
camera transforms have bounded targets, so that protocol is unaffected.

The V11 center-tile diagnostic uses one preselected tile per noisy capture across
all nine development scenes, 18 captures total. Its equal-channel DC/MSE ratio
has median 1.96%. Input-only global/per-channel CFA gain fitting worsens primary
PSNR from 47.9712 to 47.8786/47.7974; RawNIND is 49.5075 on these same center
tiles. These are different coverage from the full real suite. Do not promote an
output gain fix or attribute the main quality gap to global photometric error.

Added a source-archived diagnostic with frozen weight hashes, per-channel errors
and older-manifest ADC header fallback. Complete receipt in
docs/results/paired-bias-diagnostic.json. Full test suite: 156 passed, Ruff clean.
