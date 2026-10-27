# Independent-noise mean-loss training

**Both V124/V125 CPU/CUDA checks passed; fresh full training is queued and
quality is unmeasured. V120 remains the current general recommendation.** This experiment
follows the [conditional-noise diagnostic](conditional-noise-response.md):
weak fur/wood detail remains soft across independent noise observations.

Both arms start freshly from the same V120 Small EMA checkpoint
SHA256 a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb.
They use the cleaned **90,784-source/twenty-region** data, corrected paired32
and native128 catalogues, seed 67, 20,000 updates, LR 1e-5 with 200 warmup steps,
256×256 targets and BF16 training. The official frozen DINOv3 ConvNeXt Small,
restoration architecture, camera supervision and single-capture inference
remain those of V120.

| Arm | Simulated-noise objective | Unique targets / noisy observations per forward |
| --- | --- | --- |
| [V124 control](../configs/quality-v120-independent-noise-mean-v124.yaml) | Existing per-view reconstruction loss | 16 / 32 |
| [V125 mean loss](../configs/quality-v120-independent-noise-mean-v125.yaml) | .75 per-view loss + .25 mean-prediction loss | 16 / 32 |

The mean term applies the **same** camera-linear, rendered, edge, highlight and
auxiliary reconstruction losses to the mean of two restored outputs, against
their shared clean target. It does not average input observations or change
their noise conditioning. For squared error, this puts more relative weight on
conditional bias; the actual Charbonnier/rendered objective still needs an
empirical quality comparison. The convex mixture stays bounded below.

Each Commons/native step loads and augments 16 unique targets once, then draws
a second independent sensor observation with the identical geometry, CFA,
camera, shot/read profile, black level and 16-bit ADC. The second draw uses a
separate deterministic generator and leaves the first observation and model/data
RNG unchanged. Real paired captures retain their existing 16-observation loss;
no second observation or mean supervision is invented for them. Validation
also retains its existing single-view path.

The recipe keeps zero PSF blur, bin4 → geometry → area2, weak-texture fraction .15,
photographic contrast attenuation .25, reviewed-ROI quota .05 and normalized-band
weight 0. Reconstruction epsilons remain .0003/.0001 for simulated/paired data.
Source-loss diagnostics record the original view once per unique source,
rather than treating duplicated targets as additional inspected photographs.

## Execution and review

[Training runner](../scripts/train_noise_pair_trial.py) freezes all sources,
recipes and input manifests. Discarded CPU 128×128/B1/FP32 and CUDA 256×256/B16/BF16 checks
run 16 fresh updates plus 2 valid resumed updates per arm. They retain their
step-16 checkpoints and prepared inputs, reject changed mean weight or view count
before constructing a model, and verify the exact common parent, official
encoder, finite 91 model/EMA tensors and 89 AdamW states.

Full runs start freshly from V120 after those checks and after the exact original
V122/V123 training, quality, independent-audit, report and green-mesh owners
finish successfully. Those existing jobs and frozen sources are unchanged.
Each production worker has a prospective 48-hour limit, 24 GiB CUDA allocator cap,
64 GiB production launch headroom (56 GiB for CUDA checks) and a 32 GB runtime
available-memory floor. Internal/external
disk reserves are 96/208 GiB. No automatic retries or budget extensions.

The queued endpoint pipeline retains predictions for complete photo, known/
unseen camera, texture, color, six-region GFX and full-frame GFX evaluation.
It reuses existing controls and compares V124/V125 with V120 and V117 without
rerunning those models. Native exact-GT material triplets, all six GFX regions,
linear/sRGB16 exports, and the additional **DSCF3842/DSCF3835** green mesh under
both fixed priors are included. The ISO100 captures and their camera JPEGs are
qualitative references, not exact GT. Numeric and actual native image review
must precede a quality claim.

Local execution roots are under ".cache/current-quality-20261023-v1":

- conditional-mean-training-v2/run (controller; original worker artifacts stay in v1/run)
- V124-V125-independent-noise-quality-v2
- V124-V125-independent-noise-independent-audit-v2
- V124-V125-independent-noise-matched-review-v2
- V124-V125-green-mesh-review-v2

All four discarded checks completed 16 fresh updates plus two valid resumed
updates. The arms' first18 prepared inputs match on each device, and eight
changed-policy resumes were rejected before model construction. All91 model/EMA
tensors and89 AdamW states are finite, with Adam steps18. There were72 actual
training/encoder forwards across these checks, covering612 unique contexts and
1,190 sensor observations. Peak CUDA allocations were about12.3 GiB per arm.

Independent NumPy audits inspected301,396,702 retained array values and verified
36,208,640 variance values exactly, without Torch, new noise or neural calls.
The implementation, regression and adoption suites passed175 tests.
[Frozen plans, actual counts, source hashes and live follow-up owners](results/independent-noise-mean-training-setup-v1.json).
Full training has not started; both20,000-update runs wait for the original chain.

The [retained-output loss-gradient diagnostic](conditional-loss-gradients.md)
replays the entire objective without new neural execution. Mean weight.25
modestly raises weak-detail bias-correcting projection and lowers its
noise-associated projection. All tested camera/display/edge/CFA band
projections already support correction. The predeclared training settings
remain unchanged; the full trained comparison must establish the result.
