# Matched full-budget RAW spatial trial

Recorded: 2026-10-27T06:53:07-07:00 (America/Los_Angeles).

Prepared V131 control/V132 spatial-arm full20k continuations from V120's20k
EMA on the cleaned90,781-source/29-region corpus. Only raw_spatial_features
differs: seed70/native256/B16/BF16, one sensor view, Charbonnier, LR1e-5/warm100/
cosine20000, zero optical PSFs, reviewed quota.5, corrected paired32/native128
manifests. Feature/shadow/band/mean additions stay off. This is a full-horizon
architecture trial, separate from seed71/horizon1000 prototype checks and the
completed V129/V1301000-update precision pilot. Expected per-arm domains:
10,046 Commons/4,965 native/4,989 paired. No new quality measurement is claimed.

Executed fresh exact-recipe CPU128/B1 and CUDA256/B16 checks for both arms,
each16 updates plus an actual two-update resume. Total72 discarded optimizer/
root/encoder calls,612 target contexts. All18 input hashes match between arms
per device; initial RGB/aux outputs match65,536 CPU and4,194,304 CUDA values.
All91/89 control and114/112 spatial restoration/Adam tensors are finite at18;
all23 added tensors have finite nonzero gradients. Both changed-shadow resumes
reject before model construction. Peaks:7,041,804,800 and9,048,249,856 CUDA bytes.
An independent CPU-only reopening of all eight16/18 checkpoints verifies
1,053,314,052 finite saved values, steps and counts, first outputs/input hashes,
with no neural construction/call, noise draw, RAW decode or CUDA. All current
neural source files equal the executed source; the120 existing mean-trial
source/input bindings remain exact.

The original new controller was2242792/create1793108408.2, plan
7f3d0edbd8c59eafe2ea83e6b959d49af3a1d5e39907c84e492cfb43594487b0.
Resource review showed that admitting a long additional worker alongside V124
could consume the64GiB headroom needed to start V125. After all four check
workers exited, an owned supervisor interrupted only this new controller before
either production claim existed. Its terminal interruption receipt, source,
checkpoints, logs and all checks remain preserved. No original mean-loss owner
was signaled, and no neural prefix was repeated.

The explicit controller-only handoff adopts all four completed results, keeps
the original worker plan/source/output paths, and waits for the exact original
V125 live worker or successful completion of the whole mean trial. Current
controller2294106/create1793109048.34, plan
03fe6427a839be4994bc7311c649134c5ad9b0750bb3eb61c34e83cda7eaa600.
Both production arms retain their full20k budgets,48h worker limits,52GiB
admission,16GiB CUDA cap and32GB runtime floor. New production updates at
publication:0. The step1000 checkpoint is retained by the same live worker with
the original20k schedule; early quality collection is not yet queued.

Prepared and launched the new full-quality→independent-audit→matched-review→
two-profile green-mesh chain against this exact waiting controller. It reuses
V120/V117 and mesh controls without inference replay. The original quality-v1
plan was prepared but never launched; it remains archived. Full-GFX comparison
now pads both new models onto the same32px CFA-cell grid, returns the original
8746×11662 native output and keeps520 tiles/130 calls per model. Actual input
fingerprints must agree. Older saved grids/profiles remain recorded; comparison
images/receipts label differences instead of suggesting a model-only effect.
Focused tests exercise the real tiler on odd/even borders and native labels.

Confirmed the user's corrected extra ISO100 capture is DSCF3835, including its
cached RAF and camera JPEG. Both native160 mesh crops and fixed profiles are
queued beside DSCF3842 ISO6400. Main DSCF3879/3880, foliage/fence regions,
qualitative-reference labels and training exclusions remain in use. Originals
are untouched. No performance image or PSNR-history point is added before a
quality result; future reports include at least two native noisy/restored/GT
triplets. README/current docs now reflect the queued full trial.

Ruff passes. The focused state/admission/retention/grid/report suites and legacy
frequency/noise/shadow queue tests pass94 cases in15.63s. Current five new queue
owners are live and waiting without errors; original V124 continues. V120 is
still the general recommendation. SOTA, large weak-detail recovery, superiority
to RawNIND across the full support and100MP/10s remain unproven.

[Current trial](../docs/raw-spatial-training.md) ·
[Setup and exact owner/plan/check bindings](../docs/results/raw-spatial-training-setup-v1.json).
