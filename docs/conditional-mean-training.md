# Independent-noise mean-loss training

**V125's [6k progress review](v125-progress6000-quality.md) improves the retained
faint-ADC mean by0.136dB from4k but remains1.009dB below V120, with ordinary mean
nearly unchanged.** Fur/grass/wood fine-band response partly recovers; spatial
faint sRGB MSE remains23.1% higher than V120 and real mesh has no clear new
recovery. The separate matched eight-photo monitor gains0.0165dB over V1246k.
These supports do not isolate a broad mean-loss quality effect.
[Earlier4k review](v125-progress4000-quality.md) ·
[Earlier2k review](v125-progress2000-quality.md).

V124's original20k control is complete; V125's original20k run continues.
Both arms' CPU/CUDA checks passed. Endpoint and repeated-noise bias comparison
remain pending; V120 remains the general choice. The experiment follows the
[conditional-noise diagnosis](conditional-noise-response.md) of persistent weak
fur/wood error across independent noise observations.

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

The [retained-target coverage check](training-target-contrast-coverage.md)
finds faint-band content in these actual discarded-check batches: 31.2% of
eligible ordinary-photo blocks and44.9% of reviewed-region blocks lie below5%
contrast. Some high-count targets are flat or soft, so this short prefix does
not qualify corpus coverage or a new sampling policy. The frozen training
recipes stay unchanged while their trained bias/noise comparison remains pending.

## Execution and review

V124's original worker completed20,000 optimizer updates,320,000 unique target
contexts,560,480 sensor observations and640 validation forwards. Its endpoint
SHA256 is`d562ae2fc4e9bf903501a3db1f2192b93e465a48f150eec6de5f232d510f0cc6`.
The worker verifies finite91 model/EMA tensors and89 Adam states at20k.
The controller admitted V125 after its original64GiB launch threshold; its
20k worker is live, with budget, source and data unchanged. Full endpoint quality
still waits for the matched pair; the earlier14k measurements below are not
20k scores. [Current execution receipt](results/raw-global-only-pilot-setup-v1.json).

The completed102-input progress review reuses all V120 controls and existing
noise/RAW inputs. It includes two exact-GT native triplets, four main GFX contexts
and both corrected DSCF3842/DSCF3835 mesh regions/profiles. The measured tradeoff
is documented now; the partial checkpoint does not replace the planned endpoints
or establish the effect of the mean-loss term, which V124 does not use.
[Audited progress measurements and actual native review](v124-progress14000.md).

The newer [V1252k review](v125-progress2000-quality.md) adds14 CPU FP32 calls on
retained material, main-GFX and both corrected DSCF3835 mesh profiles, reusing all
V120 controls. It publishes two exact-GT native triplets, common40× faint displays
and both camera JPEGs. Same-budget monitoring recipes/source and81 logged training
batch hashes match between V124/V125 through2k; all2,000 input bytes were not
retained. The positive monitor triggered this review after observation. The
early V125 state remains distinct from the original endpoint comparison.

[Training runner](../scripts/train_noise_pair_trial.py) freezes all sources,
recipes and input manifests. Discarded CPU 128×128/B1/FP32 and CUDA 256×256/B16/BF16 checks
run 16 fresh updates plus 2 valid resumed updates per arm. They retain their
step-16 checkpoints and prepared inputs, reject changed mean weight or view count
before constructing a model, and verify the exact common parent, official
encoder, finite 91 model/EMA tensors and 89 AdamW states.

Full runs start freshly from V120 after those checks and after the exact original
V122/V123 training, quality, independent-audit, report and green-mesh sequence
finishes successfully. The V123 memory guard stopped its original owner and
propagated failure through the waiting dependents. An
[explicit recovery](v123-memory-guard-recovery.md) rebinds their owners while
retaining original failed receipts, source bytes, inputs and deadlines.
All four completed checks are reused. The original frequency quality/audit/
comparison/mesh owners completed; V124's fresh production completed without
repeating checks. [Completed frequency results](v122-v123-quality.md).
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

- conditional-mean-training-recovery-v5/run (controller; original worker artifacts stay in v1/run)
- V124-V125-independent-noise-quality-recovery-v4
- V124-V125-independent-noise-independent-audit-recovery-v4
- V124-V125-independent-noise-matched-review-recovery-v4
- V124-V125-green-mesh-review-recovery-v4

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
V124's20,000-update control is complete and V125's original20,000-update
worker is running. The [V124 training-start snapshot](results/v124-control-training-start-v1.json)
remains historical; [current live-owner evidence](results/v124-final-source-publication-v1.json)
records both V125 and the admitted V131 control without changing their plans.

The [retained-output loss-gradient diagnostic](conditional-loss-gradients.md)
replays the entire objective without new neural execution. Mean weight.25
modestly raises weak-detail bias-correcting projection and lowers its
noise-associated projection. All tested camera/display/edge/CFA band
projections already support correction. The predeclared training settings
remain unchanged; the full trained comparison must establish the result.

The [post-training conditional-response queue](conditional-noise-response.md#queued-trained-endpoint-comparison)
will measure the actual bias/noise change using the same 128 stored observations
per endpoint, reusing V120/V117 controls. It adds 256 new endpoint calls and
four native exact-GT triplets after the original quality/mesh owners exit.
It is a supplemental diagnostic; primary improvements can be documented first.
