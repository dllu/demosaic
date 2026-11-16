# Give competing orientations separate proposal slots

The new prototype changes how the existing CFA-wave head allocates its eight
measured carriers. **Two competing angular families receive four slots each.**
It retains the same input spectrum, native frequency band, physical CFA wave
fits, 36 readout coordinates and 643 trainable parameters. A matched 900-update
trial has completed; trained reconstruction quality is not yet measured.

This is a proposal mechanism. A second proposal is not evidence that a second
wire exists, and the learned readout can reject its output. The selector uses
both green phases and an ordinary parent restoration that has seen all RAW;
its scores are empirical features, not independent validation or confidence.

## Why test it now?

The [completed noise ladder](edge-snr-ladder.md) reaches V200 EMA strong/weak
responses of 86.7%/8.1% far from an edge under its clearest prior. The existing
selector can spend its carrier budget on one family's nearby frequencies or
harmonics. The new rule tests that competition directly, rather than increasing
response to every selected peak or increasing the number of slots.

At native 512, proposed carrier proximity to the known weaker fundamental is:

| Two-direction input / within 3 native DFT bins | Existing bank | Competing-family bank |
| --- | ---: | ---: |
| 400 prior, far edge | 26.5625% | 65.6250% |
| 400 prior, near edge | 0% | 18.7500% |
| 1600 prior, far edge | 6.2500% | 21.8750% |
| 1600 prior, near edge | 4.6875% | 6.2500% |
| 6400 prior, far edge | 1.5625% | 3.1250% |
| 6400 prior, near edge | 0% | 0% |

Each entry has 64 related CFA/repeat views from eight sources. Native carrier
distance is not a reconstruction bound: finite support, harmonics and spatial
coefficient modulation matter. The experiment is informed by these development
failures, not a blind generalization test.

There is a cost. At the 400 prior, strong-fundamental proximity falls
96.875%→89.0625% near and 67.1875%→62.5% far. The new bank still misses most weak
fundamentals near edges and in noisy inputs. In the one-direction controls,
neither selector lands within 3 bins of the absent weaker fundamental at this
prior. Background-only controls have 0–1.5625% such proximity. Those fixed-template
coincidences are not a calibrated false-activation rate for the full procedure.

## The actual operator

The strongest pooled peak defines the first orientation. The strongest eligible
peak outside its 20° angular neighborhood defines a second proposal. Remaining
slots alternate between the two neighborhoods, with the existing 3×3 conjugate
nonmaximum suppression. The rule treats orientations modulo π and preserves
native sensor coordinates; it does not resize one green phase onto the other.

The native 1/64…1/3 band remains intact, including the earlier 27.69-pixel
fundamental. Both per-color wave amplitudes and physical phase transport still
come from actual CFA measurements. Allocation changes selection and therefore
the local contexts/waves evaluated at those carriers; this is a practical
measurement intervention, not an isolated claim about one scalar score.

All 768 CPU selector calls close before target-geometry scoring. Six first-batch
CPU/GPU bridges reproduce all integer selections exactly. No neural forward,
parent inference, new source/noise draw or protected-media access occurs in
this proposal diagnostic. A principal-Nyquist sign convention was corrected in
the geometry scorer after closure; zero scored values changed and no selection
was replayed. The original source/receipts remain preserved.
[Exact selections and scoring](results/competing-phase-v1/publication.json).

## Matched training and review

The [recipe](../configs/experiments/orientation-balanced.json) uses the exact
V200 data cache/pair units, V195 anchor, seed 202611080198, 1,000 scheduled rows,
900 noisy updates, optimizer and ten-term objective. No new training images or
noise are constructed. The new model kind is `orientation-balanced-cfa-wave`;
existing kinds retain their previous default selector and checkpoint formats.

Admission proves all 197 initial state tensors are identical to the standard
model. Four-CFA noisy/ADC tests check 393,216 exact output channels, zero-output
initialization and unchanged ADC routing. A real training-only batch verifies
finite gradients on exactly four tensors/643 parameters and no frozen gradient.
Admission performs zero optimizer updates; its probe is never an initializer.

All 1,000 rows completed: 900 noisy updates and 100 exact ADC skips. The audit
confirms the frozen-state hash and original domain counts (307 mesh, 214 photo,
141 flat, 139 mixed, 99 weak). [Training completion](results/competing-phase-v1/training-completed.json).

The live pipeline evaluates both endpoints on all 822 existing quality inputs and
all 60 native boards, including the protected main/cab scenes, both cab profiles
and both JPEGs. A second queued worker then reuses all three fresh-noise caches,
with independent role/repeat noise, for actual weak/quiet gain curves. It checks
the inherited anchor against saved V195 pixels and actual full-forward delivery
before interpretation. No existing scientific prefix is restarted.

The review runner now has an explicit model-intervention mode that requires
unchanged training data and initializer; it records the model change and gives
figures the correct candidate label. Source snapshots, exact process identities,
checkpoint rows and launch evidence are [retained](results/competing-phase-v1/launch.json).
That launch observation records the earlier row 705; it is preserved unchanged.
No current recommendation changes until actual strengths and failures are
measured. The earlier [shared-edge](shared-edge-comparison.md) and
[analytic edge-fit](withheld-cfa-edge-refinement.md) results remain available.

```bash
source scripts/env.sh
uv run demosaic-experiment prepare configs/experiments/orientation-balanced.json \
  .cache/experiments/competing-new
uv run demosaic-experiment launch .cache/experiments/competing-new
```
