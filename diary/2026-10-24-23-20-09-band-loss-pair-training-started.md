# V114-parent band-loss pair passes CPU/CUDA checks and starts training

Recorded: 2026-10-24T23:20:09-07:00 (America/Los_Angeles).

The completed V116 data intervention left broad weak-material gain unchanged,
despite a stronger eight-pixel analytic carrier and a worse ADC color tail.
The next full trial therefore uses V114 as its explicit parent and tests the
existing optional contrast-normalized band objective. V117 weight0 and V118
weight.0003 share seed64, fresh AdamW/EMA,20k updates, the90,864-source corpus,
legacy weak profile, corrected paired masks, zero optical blur and native256/B16.
It changes one loss coefficient, with paired RAW retaining its original loss.
The earlier mixed local-gradient/first-Adam probes do not predict trained quality.

A CPU metadata check finds native patch coverage256/320/384/512 of
90,864/55,998/24,753/1,762 sources at the existing4×→area2 geometry. A global512
change would substantially change the corpus. This loss trial keeps geometry
and batch size fixed. No raw source drive is opened or source photograph changed.

The recipe preparer now supports artifacts inside its own frozen workspace.
Internal phase/runtime reserves are128/96GiB; external cached inputs retain
208GiB. Legacy external thresholds remain unchanged. Six boundary/resource tests
pass. All new artifacts stay on the internal SSD; parent models/cache inputs
remain read-only. Model choice and historical receipts can advance independently
because each run freezes its explicit parent selection.

Preparation makes zero neural/module calls and no CUDA allocation. The full
physical source/data payload matches completed V116's archive byte for byte,
SHA707abdcea6f3e14a48a7d6ebc7f1769e3da8e96d8959d856fcfc32961787075b.
The new parent is V114 SHA2285c84b7015bcf122e71b890723f80aaf216bde849256c77f070c2493f9d2d2.
The original controller2091984/1792908264.52 verifies successful exit of all
original V116 owners before new work; its execution plan SHA is
b455b25dce789a12de094147428d4f550c31fde255e293ce13bd437582504246.

Both arms pass eight discarded CPU64/B1/FP32 and eight native256/B16/BF16 CUDA
updates:32 actual optimizer updates total. All91 initial EMA tensors match V114;
all89 fresh Adam states reach step8 with finite model/EMA/optimizer. The official
Tiny encoder remains frozen with no gradients. Each prefix has four paired,
one native and three Commons batches, with exact cross-arm input fingerprints
and initial predictions. The control evaluates no band term; each candidate
check evaluates it on four synthetic/native batches, with none on paired RAW.
At the first unpaired step4, the candidate loss exactly equals the FP32 control
loss plus.0003 times the band term. These are readiness checks, not quality gains.

Production starts fresh from V114. V117 worker2093175/1792908446.50 is running
its original20k budget. Its first4,194,304 FP32 output values and first loss match
its own discarded CUDA check exactly. The immutable publication prefix ends at
775 logged steps with finite loss/gradient-norm/LR; it does not count in-flight
updates or prove completed training. The worker checks first-eight clean/noisy
inputs against its own CUDA check and reuses existing production trace hashes,
avoiding duplicate hashing of each logged batch.

Prospective domain batches per arm are5,013 paired/4,955 native/10,032 Commons;
V118 plans14,987 band evaluations and V117 zero. These are planned counts;
full actual counts will be recorded on success. V118 production follows V117
within the same unchanged controller. Failures preserve all evidence and stop
without automatic retry or extra training budget.

Exact downstream owners2094018/1792908597.16 and2094020/1792908598.57 are live
for full quality and independent CPU audit. They declare9,172 new model/encoder
calls,28,380 numerical observations, all eight panels/stages, at least two
native160 noisy/restored/exact-GT triplets per model, all six standing GFX regions
and complete102MP outputs. Existing controls are reused without neural reruns.
The final contrasts must show V118 versus its matched V117 control and both
against retained F64 V114 outputs, with local weak-detail/color/native review.
No original V116 source, receipt, output or successful neural work was repeated.

[Current trial](../docs/band-loss-training.md) ·
[Completed readiness and live-run receipt](../docs/results/v114-band-loss-training-started-v1.json).
README/current guides now point to this active trial. V114 remains the general
model; its optional inference modes and the49 completed primary history points
remain unchanged. This publication adds no neural calls, optimizer updates,
noise observations or RAW decodes.

