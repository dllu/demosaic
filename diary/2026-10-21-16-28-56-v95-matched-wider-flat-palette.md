# V95 matched wider flat palette quality follow-up

Recorded: 2026-10-21T16:28:56-07:00 (America/Los_Angeles).

Follow the completed V93–V95 review with a matched quality stage from V95's
final EMA. Its photographic and weak-detail gains coexist with worse
high-noise saturated-color tails. Test the existing 0/8-stop smooth-field
palette option under the original V43 architecture; retain the curated
88,484-source corpus, zero optical PSFs, weak-detail/photo-contrast recipe,
domain fractions and all fixed validation/native/paired inputs. Seed 57,
batch 16, native256, BF16, fresh optimizer/EMA, 4,000 equal updates. Final
4k checkpoints are primary, intermediate/best checkpoints diagnostic.

The actual 256-sample clean-data check sees all five source routes and changes
only its 20 colored smooth fields; 1,000 generator pairs preserve Python RNG,
including 512 exact neutral fields. The deterministic full schedule changes
1,618 colored-field patches among 64,000 planned patches. Bright clipping can
alter means; affected Poisson draws need not match. Paired/native observations
must match, and production's first24 inputs must match its own discarded CUDA
probe. The 23 existing palette/routing/fine-detail tests pass.

The first launch exposed my shared worker CLI omission: it accepted only
V93/V94/V95. CPU V96 exited2 during argparse, before training. Preserve v1
plan/logs and actual readings. Expand the CLI names and explicitly prepare
and launch a fresh v2 namespace, with no automatic retry or threshold change.
V2 plan SHA `3fcc5b72cf781e844238cdefc696f73c05b4540935226742bb39b3588ed2b706`;
launch receipt SHA `d6e2498ed994b1eabb4eac48118d48090edef9a21a46cd995c459dfd6305f384`.
Actual controller PID3838388/create1792625353.89 starts in the resource wait;
CPU/CUDA preflights and production are pending at that launch observation.

Generalize saved-state audit expectations to the frozen stage length/parent,
and add an explicit palette evaluation mode for V43/V95/V96/V97. Color lineage
checks retain the exact checkpoint step and full initializer path/hash/step
for multistage training. Seventeen focused lineage/resource tests pass,
including rejection of wrong boundaries and wrong initializer identities.
These tests do not qualify actual model inference or held-out quality.

The [prospective plan](../docs/v95-flat-palette-quality-plan.md) records scope,
resource policy and the required full primary/analytic/color/GFX/native review.
Keep V43 as the working reference; no quality, speed or promotion claim yet.

All four actual preflights subsequently complete: CPU/CUDA × V96/V97,
24 updates each, totaling 96 training/DINO forwards and optimizer steps.
Each phase preserves all 12 paired/native batch observations exactly;
one CPU and nine CUDA affected Commons batches differ. Initial model hash
is `8c8646e5e984148338748423fbb97b36143b9d14b494b8f7844520c282c826f3`,
frozen DINO `35035ba142eb119cd5980cf0d9809bfa28f622538c259ffb0fcf348ca6e68898`,
and numerical source `ea9622343d2ad4d9f12ea0089884ad9dcefb87be4ae06f24eacc764829c02d09`
for every proof. Independently read all four actual checkpoint states with
CUDA hidden: each has 71 finite model tensors, 71 finite EMA tensors and
69 finite Adam states at step24, exact stage lineage/configuration and finite
loss/gradient records. All proof owners are exited.

Observe actual V96 production PID3845032/create1792625778.91 beyond step25,
loss0.0116215553/gradient1.22059512, under the same live controller. No new
checkpoint or held-out quality claim. Publish the
[preflight/production-launch receipt](../docs/results/v95-palette-preflights-and-training-launch-v1.json),
SHA `a0cf083161f4c65671138c72997e30c0ca305f428ce8bd23112d9e21dd0532e3`.
The executed CPU-only receipt producer is archived/hash-bound with the plan.
V97 follows serially; final4k independent audits and the complete fresh FP32
quality/native review remain required. Forty focused tests and Ruff pass.

