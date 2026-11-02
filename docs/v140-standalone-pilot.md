# Standalone V140 patch-memory pilot

**V140 is now being trained on its checked 1,000-update recipe. Quality remains
unmeasured; V120 Small stays the general recommendation.** The new execution
separates this previously unstarted pilot from the failed October dependency
chain. [Execution audit and frozen plans](results/v140-standalone-setup-v1.json).

The earlier V125 and V131 workers both stopped at the 32 GB available-memory
floor, and their dependent controllers exited. They are not still running.
Their saved steps are8,799/14,549 of20k. Partial checkpoints, original plans, logs, failed receipts and completed
checks remain intact. This is a new, explicit run of V140, rather than a restart
of either long worker or an extension of their training budgets.

V140's hypothesis is that neighboring RAW-gradient arrangements help match
repeated faint structure. The implementation adds a learned neighborhood
descriptor before memory attention. Every output feature passes through memory;
the direct local shortcut used in V137 is absent. The architecture remains
[the already checked patch-memory operator](raw-patch-memory.md).

The recipe starts freshly from V120's 20k EMA, with the original frozen 69-module
training source, 90,782 photos/27 reviewed regions, seed70, 50% reviewed-region
quota, native256/B16/BF16, zero optical PSF, LR.001 and100 warmup updates.
Only16 branch tensors/16,192 parameters train. All91 parent model/EMA tensors
must remain exact. Each of1,000 clean/noisy training batches must match saved
V137 witnesses. Existing CPU/CUDA16+2 checks are adopted without replay.

This run can establish whether the full branch provides useful quality, but
comparison with V137 changes operator, training scope and branch learning rate.
It does not isolate the neighborhood descriptor against V139, whose production
run remains unstarted. No architecture promotion depends on completing that
historical execution chain.

The standalone source package includes dependency and third-party license files
required by the trainer's source snapshot. Two earlier startup attempts exposed
missing assets before model construction; their logs are preserved. The corrected
worker has executed real updates with matched input witnesses. The12GiB CUDA
cap,50GiB launch RAM,32GB runtime floor and original8h worker timeout remain.
No `/mnt/dataz` access is needed. The targeted feature/scope/analytic-metric
suite passes38 tests. An initial invocation named a nonexistent test file; the
first collected run then found an overly tight FP64 plane-fit tolerance in the
new test. Correcting that tolerance leaves the metric code unchanged.

## Fixed review support

The review declares102 new IEEE-FP32 neural calls on64 shadow,16 ordinary,
16 faint-ADC, four main DSCF3879/3880 contexts and two DSCF3842/DSCF3835 mesh
profiles. It reuses408 predictions from V120/V129/V136/V137. Sources, coordinates,
input bytes, conditioning, display exposure and source-defined masks stay fixed.
Exact synthetic targets receive native160px noisy/restored/GT triplets; binned
references and independent ISO100 captures retain their approximate labels.
Both protected GFX scenes, foliage, fences, sky and building detail are included.
Both camera JPEGs accompany the extra mesh. Numeric and actual native-image
review are required before a quality claim.

A separate48-input flat check was fixed before seeing the trained results:
neutral levels.02/.18/.90, dark/mid blue and dark green, ADC-only/ISO12800 priors,
all four Bayer layouts and one existing observation per case. All V120 outputs
are reused. Exact analytic targets support DC color error, centered spatial MSE
and4/16/32px block-average error. Broad splotches remain visible in the coarse
terms. The real sky receives affine-detrended spatial measurements; these are
descriptive variation, not false-detail error against exact GT.

The faint supplement uses the existing original-source DCT strata and camera/
sRGB DC/spatial decomposition. Its common40× contrast display is never scored.
The support remains four material contexts, one draw per CFA, and a small color
subset. It does not establish full427-photo/camera/color quality, full-frame
seams, speed, conditional bias or broad real-camera superiority.

Runners: [training](../scripts/run_standalone_patch_memory_pilot.py),
[matched review](../scripts/review_standalone_patch_memory_pilot.py),
[flat safety](../scripts/report_pilot_flat_safety.py).
