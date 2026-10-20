# Preserve resume logs and remove unused inverse work

The untouched original4k control reached3,650 at03:25UTC. Its retained2k state
has91 finite model/EMA tensors and89 finite AdamW states, counters2k and original
cosine LR5.681196730492369e-6. All30 discarded recorded batch/forward/loss
observations and all31 recorded loss/gradient/LR/domain fingerprints replay
exactly. The31st metric row is the real first-resume update1,001.

That extra row exposes a second production-only completion bug: the frozen
worker expects only first/every25 logs after finishing and saving4k. Added an
explicit source-frozen CPU completion coordinator that leaves the active
controller557934/1792464246.16 and worker558182/1792464315.65 untouched. Only
after their genuine exits does it accept the specific final log assertion,
audit saved4k state, preserve162 actual logs and176 observations, and launch
the unchanged fresh spectral worker for its original4k. No control update,
schedule extension, model/data/noise/criteria change or new direct final
DINO-memory measurement is claimed.

Coordinator620536/1792466470.15 is live at
`spectral-v88-v89-log-completion-v1`, planSHA
e595dfb8808cb33b0d147047e4a33519ee612c5281061275356d16f6c6d59cf4.
Five exact idle old review/closure/reference/package/inverse-probe owners
were explicitly cancelled and verified exited; no training owner was touched.

Focused metadata tests:42 passed. Fresh CPU integration v3 audited the genuine
CPU/CUDA16 engineering states, refused incomplete production and engineering
quality inference, replayed all historical thresholds exactly, and reproduced
all20 native asset PNGs without changing their bytes. No new quality inference
or manual-view claim. ReceiptSHA
7e0e51976c373e9668dc20fa717b28b7a2e53ce6d04fefb9b57a49417504ad1c.

Full original4k review is now frozen at
`spectral-v88-v89-final-log-review-v2`, planSHA
753f0fca62747cf3dd4646d31e81fd33942f40dad82c00388c31059d345e84a0,
296 frozen files/all46 actual archived training modules. Review622316/
1792466582.56, closure622318/1792466582.66, reference622325/1792466582.86 and
native package622507/1792466628.77 are live and waiting. Actual native viewing
and numerical interpretation still follow both original training budgets.

Separately removed eagerly computed/discarded closed-form arithmetic from
the VST table inverse. Only the inverse method changes; a fixture preserves
the original archived body. CPU verification:58 pass/one CUDA-only skip,
including output/input-gradient byte parity across modes, profiles, dtypes,
table boundaries/tails and noncontiguous inputs. The full genuine V63 model
also produces byte-identical61,440 RGB values on four cached GFX80×64 crops,
with identical weights/RNG. CPU ATen dispatches56→39, cubed elements15,360→0;
these are not CUDA kernel counts or speed results. Ruff lint and diff checks
pass. The formatter accepts all eight checked metadata/test/probe files; its
single VST complaint is an unchanged pre-existing long assignment.

The isolated CUDA inverse probe622509/1792466628.84 waits behind all exact
training/review/closure/reference/package exits, at`vst-unused-inverse-CUDA-v2`,
planSHAc8de5a6abfc923fbb1f42da870ee69f672d58795b19cbdfbf84f047be2f74f1a.
It reuses the unchanged first candidate snapshot. No GPU timing result,
full-model/full-frame acceleration or quality benefit is established. Active
training and evaluation still use original VST355124a3…, not this cleanup.

Evidence and details: [resume-log completion](../docs/spectral-log-completion.md),
[queue receipt](../docs/results/spectral-log-completion-queue-v1.json),
[exact replay/2k state](../docs/results/spectral-replay-and-step2000-v1.json),
[inverse cleanup](../docs/vst-unused-inverse.md),
[CPU model parity](../docs/results/vst-unused-inverse-CPU-v1.json).

The PROMPT objective remains active. No new model is promoted; SOTA/native
superiority and the100MP/10s target remain unproven/unmet. Source originals and
spinning disks were untouched.
