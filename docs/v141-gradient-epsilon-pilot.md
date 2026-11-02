# V141: stronger supervision of small spatial-gradient errors

**V141 is training its fixed1,000-update pilot; restoration quality is not yet
measured.** CPU128/B1/FP32 and CUDA256/B16/BF16 checks each passed16 updates and
a genuine two-update resume. All36 clean/noisy batches match saved V129. The
first CPU/CUDA outputs match4,259,840 saved parent-output values exactly.
[Execution, source, checks and predeclared reviews](results/v141-gradient-epsilon-setup-v1.json).

V140's [complete native/flat review](v140-standalone-pilot.md) found almost no
output change or new mesh recovery. A [six-context branch check](results/v140-memory-amplitude-v1.json)
finds the trained memory returns about.97–1.60% of combined token RMS before
the final projections. These are feature units on reconstructed CPU training
contexts, not final-image error or a causal explanation of the real fence.
It motivates testing a loss change through the existing full restoration path.

## The isolated change

V141 keeps V129's architecture, V12020k EMA parent,90,782 photos/27 reviewed
regions,seed70,50% reviewed-region quota,native256/B16/BF16,zero optical PSF,
LR1e−5,100 warmup updates and1,000-step cosine horizon. All1,000 clean/noisy
training batches must match the saved actual V129 control. The official DINOv3
Small encoder stays frozen;89 restoration parameter tensors train normally.
Existing V129 training and predictions are reused.

Only the Charbonnier smoothing scale for the existing horizontal/vertical
**rendered-gradient error** changes from.0003 to.00003. Its coefficient stays.1.
Camera-linear, rendered-pixel and auxiliary epsilons remain.0003; highlight,
validity masks, noise simulation and every other loss coefficient stay fixed.
The real-paired measured-CFA/coarse-rendered objective stays unchanged.

The scalar derivative is`e/sqrt(e²+epsilon²)`. Reducing epsilon strengthens
small residual gradients while keeping the same bounded large-error influence.
It weights gradient **errors**, rather than selecting weak clean-target edges.
On a uniform target the correct gradient is zero, so invented variation receives
the same matching penalty. This is a rationale to test, not proof against
hallucinations after training.

```yaml
reconstruction_charbonnier_epsilon: 0.0003
gradient_charbonnier_epsilon: 0.00003
```

Missing/None gradient epsilon inherits the pixel epsilon exactly, including
legacy checkpoints. Positive finite values with safe FP32 squares are required.
Checkpoints store the effective value; changed pixel or gradient epsilon rejects
before model construction on resume. Direct, grouped and conditional-mean loss
paths and source diagnostics receive the same setting. Inference has no new
option, transform or learned architecture.

## Review and present limits

The fixed review has102 new IEEE-FP32 candidate calls:64 shadow,16 ordinary,
16 faint-ADC,four main-GFX512 and two extra-mesh768 inputs. It reuses408 saved
V120/V129/V136/V137 predictions. Identical coordinates, inputs, noise conditioning,
source-defined masks and display transforms remain fixed. Exact synthetic
targets receive native160 noisy/restored/GT triplets; binned and independent
ISO100 references remain approximate, **not GT**.

Both protected DSCF3879/3880 and DSCF3842/3835 pairs remain out of training,
along with their JPEGs and siblings. Foliage, fences, sky, building and both
fixed mesh profiles are included. The extra mesh includes both camera JPEGs.
Only existing cached arrays/media are used; `/mnt/dataz` is unnecessary.

A separate48-call exact uniform-color check reuses the same V120 observations/
outputs as V140: six neutral/blue/green colors,two conditions,all four CFAs.
It measures DC color error, spatial residual and4/16/32px block-average error.
The real sky's affine-detrended variation is descriptive, not photographic GT
error. Existing flat operators receive label/path-only frozen variants, keeping
V140's operator bytes and receipt bindings unchanged.

The main70-test suite covers default exactness, gradient-only changes, correction of
missing weak structure and spurious flat texture, actual grouped mixed-domain
training, legacy inheritance and exact resumed model/EMA/Adam/RNG states. A further34 noise-pair/faint-analysis checks pass. Both
production-shaped checks pass all input hashes, finite91 model/EMA tensors and
89 Adam states at18, plus changed-policy rejection before construction.

Resources remain12GiB CUDA allocation,40/50GiB CPU/CUDA launch RAM,32GB runtime
available-memory floor and8h production limit, with no automatic retry or horizon
reset. The short checks are discarded; production starts freshly from V120.
Native, numerical and flat audits and actual viewing must precede a quality
claim. This pilot does not yet establish any image improvement, full427-photo/
camera/color quality, full-frame seams, speed or broad superiority.

[Recipe](../configs/quality-v120-gradient-epsilon-pilot-v141.yaml) ·
[Trainer](../scripts/train_gradient_epsilon_pilot.py) ·
[Review driver](../scripts/review_gradient_epsilon_pilot.py) ·
[Tests](../tests/test_gradient_epsilon.py).
