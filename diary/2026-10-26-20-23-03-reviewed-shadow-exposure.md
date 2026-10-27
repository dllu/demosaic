# Prepare reviewed material shadow exposures with CPU and CUDA checks

Recorded: 2026-10-26T20:23:03-07:00 (America/Los_Angeles).

Extended the retained-target analysis into shadows and sensor units. The earlier
.02 rendered-luma filter omitted1,064 ordinary-photo and2,472 native blocks.
The new NumPy analysis reuses272 simulated target slots, excluding16 real-paired
slots without known pre-noise inputs. It measures the actual128 green CFA sites
in each native16 block, separating their mean and pre-ADC pixel-noise RMS from
rendered-luma fine-band contrast. This is not luma-band SNR or calibrated
real-camera noise. Native simulated targets retain source noise/optics.

In this18-step implementation prefix, there are937/63/2,305 valid shadow blocks
from ordinary/reviewed/native targets, including240/13/173 weak shadow blocks.
The existing DSCF3842 mesh regions have observed-green means.005871/.006489.
Their two fixed profile proxies fall in the coarse brightness[2^-8,2^-6),
relative pixel-noise RMS[.5,1) cell. It contains6 ordinary and22 native weak
blocks, but none from the seven reviewed-region draws. This is not a population
absence claim: neighboring3x3 cells contain161 ordinary,174 native and400
procedural weak blocks. The right nearby-profile proxy.5022 is near the.5
boundary, with no calibrated uncertainty interval. The two private train scenes
and siblings stay out of training; only retained GFX input arrays are read.

Independent native-pixel masks check all27,200 blocks, all validity/condition
bins and four GFX ROI/profile combinations. Green means are exact; maximum
variance and relative-noise differences are4.34e-19 and1.43e-14. This coverage
extension generates no neural call, noise observation, RAW decode or optimizer
update. Its purpose is to motivate a prospective data intervention, not to
diagnose the mesh failure or certify corpus adequacy.

Implemented default-off `reviewed_shadow_fraction` with versioned
`reviewed-shadow-green-v1`. Only existing reviewed Commons material crops can
be selected. A local per-source stream samples requested dense camera-green
means log-uniformly2^-10..2^-5; one exposure scalar is bounded1/64..1 of the
unexposed source. Requested means may be limited by that bound. Source geometry,
color ratios, camera/WB/CFA/shot/read/ADC settings are preserved. No additional
interpolation, PSF or contrast attenuation is introduced. Both independent
noise views share the new target and metadata; native/paired/validation paths
bypass it. Changed fraction/policy is rejected before model construction on
resume, and source-loss diagnostics record selection, request and actual gain.

The actual reader validates all20 latest90783-bank regions and prepares28
native256 contexts once (20 regions,4 ordinary,4 procedural). Frozen legacy,
new zero-policy and enabled-policy preparation reuse that geometry on CPU and
CUDA, with B16 plus partialB12 and two observations per target. This fraction1,
forced-Commons engineering proof is not a production prefix. All six workers
complete12 preparation calls and336 sensor observations, with0 neural/encoder
calls,0 optimizer updates and0 RAW decodes. CUDA peaks at183,521,792 allocated
bytes under the2GiB cap. Worker global Python/Torch CPU/CUDA RNG states are
unchanged outside the seeded context. Actual runtime source bytes match the
public implementation exactly.

NumPy verifies69,733,440 old/default preparation-array values bit-exact,
11,010,048 RGB values equal to source times recorded scalar exactly,
12,582,912 unselected target values unchanged and7,340,032 candidate variance
values exact. All camera/noise settings match; targets/metadata match across
the two views. Maximum clean/target/gain oracle differences are3.29e-7,
1.71e-7 and2.36e-8. CPU reviewed-green median shifts.126023→.005749; CUDA
.145069→.005747. Both shadow ranges are.001049–.028373, with4/5 cases at the
minimum gain bound. Poisson stream consumption can change other noisy pixels
within an affected batch; per-step seeding and saved state support resume.

The regression run passes104 tests with one optional hardware case skipped
under the CPU test environment. Separate actual CUDA preparation is complete.
Tests include full versus2+2 resumed local-model/EMA/optimizer/RNG equality,
disabled behavior, metadata logging, independent noise views and domain bypass.
Those small local-model updates are disposable implementation fixtures; the
data-only proof above has no neural execution or trained-quality result.
One initial analytic fixture requested a mean below the gain floor; the code
correctly clipped it. The fixture now checks a reachable mean and separately
asserts the bound. Ruff passes.

Actually viewed both descriptive charts and published their original PNG/SVG
bytes, source/data bindings and complete CPU/CUDA/coverage receipts. Trained
quality remains unmeasured. The half-probability config example is a future
experiment, with no parent chosen or full run queued. Use the best useful
architectural baseline after the current outcomes rather than freezing a
historical choice. Active V122/V123 retain90786/14 and queued V124/V125 retain
90784/20; both original input guards pass. V120 stays the recommendation.
All twelve exact job owners are live; V123 reaches update8,650 at the latest
check. RAM available73.7GiB; internal/external free644.9/222.9GiB.

[Implementation and readiness](../docs/reviewed-shadow-exposure.md) ·
[Actual CPU/CUDA and independent proof](../docs/results/reviewed-shadow-exposure-readiness-v1.json) ·
[Shadow conditioning and neighboring-cell sensitivity](../docs/results/shadow-sensor-coverage-v1.json) ·
[Current target-coverage report](../docs/training-target-contrast-coverage.md).
