# Close the complete spectral quality review and deferred CUDA probes

This goal turn made progress. The previous turn also made progress by viewing
and publishing the retained camera comparisons. Both original4k training
budgets are now followed by the complete actual quality/native review, with
an explicit decision to promote/extend neither endpoint. The full project
objective remains active, with SOTA/native superiority and100MP/10s unmet or
unproven.

The exact full427 worker703974/create1792471179.23 completed74,424 rows and
exited successfully. All ten original stages then completed under the exact
review controller622316/create1792466582.56. CPU closure, retained references,
and native packaging completed after their required predecessor exits.
There was no restarted inference, modified quality threshold, protected-final
test, extra training budget or new full102MP export.

I actually viewed all eight fixed native boards before interpreting new model
quality statistics:81 source triplets/125 unchanged160px cells. The early
photo board was revalidated after its producer exited, including all original
source/ROI/conditioning/display/common-input/restored pixels; its final PNG
is byte-identical. Every final board matches an actually viewed image hash.
Two local early-photo packaging mistakes were corrected without changing the
producer: PNGs must be copied inside their report directory, and read_crop
requires a Path rather than a string. The completed source/pixel validation
passes; failed intermediate packaging artifacts are not quality evidence.

The pre-statistics actual-view receipt is
`spectral-v88-v89-final-log-review-v2/manual-native-review-before-statistics.json`,
SHA256`2e21bc943afc7d8bbafbd32eca87dd9392f3db27ca780db7342711c1bd038974`.
All source and report paths here are below
`/mnt/external/demosaic/experiments/` unless otherwise stated.

V89−V88 photographic PSNR is+.007760dB, source-bootstrap interval
[+.006946,+.008511]. SSIM changes−.0001479, concentrated in the overexposure
condition (−.001222). ADC-only photo gain is+.02869dB, highest-noise gain
only+.00135dB. Against fresh V63, photo gains are+.25625/+.26401dB but known
camera changes are−.02141/−.02512dB, with negative source intervals. Unseen
changes+.04896/+.05082dB leave V88 just below its original minimum. Both
endpoints fail the known-camera promotion requirement.

The two fixed carrier improvements are+.010615/+.016657, below+.05. Flat RMS
ratios.99780/1.00282 pass. All192 individual ADC changes pass−.05, ranging
−.023701 to+.024668, with all twelve means retained. I independently
recomputed every one of those192 differences and12 means from the actual
per-case rows after viewing the boards. The418/416 photo exclusions preserve
the small PSNR gain and SSIM loss; this is source sensitivity, not an
independent final test or training-seed uncertainty estimate.

The complete raw-score coverage/summary, source/Decimal/bootstrap,1344-case
analytic arithmetic,3528 float-prediction/21,168-field color arithmetic and
648-field color summary checks pass. The color grid remains mixed: bright
colored fields improve versus V63 while bright gray mean bias worsens.
All27 classical witnesses are exact. These audits are scoped to stored
scalars/arrays as documented, not a claim of independent full-photo prediction
recomputation or SOTA.

The GFX sky/building/foliage/fence, sign and platform views retain no clear
new spectral detail advantage. The project models preserve the selected
fence grid better than RawNIND; foliage remains overly smooth and blue-sign
fine structure remains suppressed. DSCF3879/3880 remain different time/aperture
captures with an independent ISO100 reference, not exact GT. No source HDD
was needed, no original was modified, and the scene/siblings remain outside
training.

`docs/spectral-original4k-review.md` publishes the complete decision, four exact
GT triplets, eight GFX triplets, all eight native boards and full metadata.
Twenty published assets match packaged bytes, including reused GT/camera
PNGs. The final decision receipt is
`spectral-v88-v89-final-log-review-v2/final-quality-review.json`,
SHA256`8aa5d62feb8bd5e073276a0f55d2473f913da993028b70c60641484166a3a3bf`.
README/current requirements link the completed result; V43 remains working.

Both deferred implementation probes also completed in their exact serial
order. VST inverse outputs (3,194,880 values) and sampled input gradients
match byte-for-byte; native512 medians are about1.82→1.17ms. All six physical
feature tensors match bytes/strides across59,637,792 values; B4/native512
channels-last medians are5.10237→4.04150ms. CPU/CUDA RNG is unchanged in both.
These five-sample alternating component timings are not a full neural-forward,
training-throughput, memory-peak or100MP speed result. Full results are in
`docs/unused-physics-work-CUDA-review.md` and its bound result files.

The separate width-fold CPU study was also completed/pushed as6b46257 earlier
this turn; its dense representation raises current trunk MACs97.68% and has
no measured GB10 speedup. It did not enter the quality trial. No new GPU job
was launched from that study.

Publication byte checks, all eight board validators, local Markdown/image
links, Ruff lint/format and diff checks pass. Next, inspect learned spectral
gate/innovation behavior on the fixed analytic observations before choosing
another quality intervention. The fixed trial does not support an extension
based solely on the small photo gain.
