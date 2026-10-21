# Record resource readings and verify V95 suspension and continuation

Recorded: 2026-10-21T11:13:31-07:00 (America/Los_Angeles).

The first explicit recovery later stopped around logged step1,550, still before
any saved training checkpoint. Actual controller PID3351332/create1792603701.53
and worker PID3351636/create1792603763.29 are exited. The recorded error remains
the generic `AssertionError('Training resource floor')`.

Correct the earlier causal wording: neither the original guard near1,025 nor
this second guard records which contemporaneous resource crossed its limit.
Low system-disk space was directly observed at the first recovery and prevented
a fresh start; that observation does not establish the cause of either earlier
stop. Preserve the prior machine receipts and snapshots as historical evidence,
and record this clarification explicitly in current documentation/new evidence.
Both partial unsaved trials, logs, claims and failed status copies are archived
with byte hashes and original-path mappings. V93/V94 remain completed and intact.

Add exact resource readings to `scripts/recover_v43_quality_trial.py`: available
RAM, root/external free bytes, external mount identity and timestamp every2s,
including the actual sample in a failure. Retain the original RAM24/root64/
external384 GiB active thresholds and48 GiB/stable60s launch thresholds. If only
disk/mount reserves fail while RAM remains adequate, suspend only the owned
process group. Resume that same PID after original launch thresholds remain
stable60s and both frozen input guards pass. RAM below24 GiB still terminates
the group. Disk wait remains bounded7200s and the original48h stage wall-time
bound includes suspension. No numerical worker/configuration/data change or
automatic training retry is introduced.

A new actual CPU process-group integration test covers an owned parent and
child: wrong PID/create-time rejected before signaling, both counters stop and
resume with identities preserved, and SIGTERM/SIGCONT cleans up a stopped group.
One test passes with CUDA hidden and no model/inference. Also observe resources
for180s before the next explicit attempt: no below-floor samples, with minima
about70.75 GiB RAM /77.73 GiB root /462.00 GiB external. These samples establish
current headroom, rather than retrospectively identifying a previous trigger.

Prepare the fresh recovery at
`.cache/quality-first-20261020/V95-manual-recovery-v2/`, plan SHA
`68f43182e585848a4b7c9667dcfe112168f4d4c63dae74d5040cbce1a9ab71a9`.
It references the unchanged original numerical training plan
`2fec2f3e77e15791d1ece4e10e65133a84be234eba0702a4d4dcd643753f7556`,
completed controls and all six passed preflights. The failed second trial is
archived separately. Actual controller PID3422254/create1792605923.15 and worker
PID3422418/create1792605984.94 are live on a fresh V95 stage from original V43
step2000, with the same seed/schedule/augmentation/precision.

Test a controlled3s SIGSTOP/SIGCONT on that actual CUDA worker after it is
training. Host metric bytes remain unchanged while stopped; the same worker
resumes and advances with finite recorded losses/gradients. This checks actual
CUDA operational continuation, not bitwise learned-state parity or image
quality. CUDA continuation receipt:
`6eb4f6b2e9b3689201aef772b3fec58b1665b6aad8697483497bbf4770ddbc20`.

The subsequent immutable snapshot records training through logged step1,950.
All63 scheduled recorded batch fingerprints through the archived1,550 prefix
match exactly. This does not claim that all unlogged intermediate batches or
floating-point training states were compared. Exact resource-history snapshot
and recorded-prefix receipt:
`11fea49950c5a3f5606da9769de7f090b50f7a0095eece24e087aeaabdaaf62c`.
No automatic reserve-triggered suspension had occurred in that snapshot; the
controlled CPU/CUDA checks do not substitute for a real reserve event.

[Published telemetry/recovery evidence](../docs/results/v43-quality-V95-resource-telemetry-recovery-v2.json)
records the causal correction and actual observations. Ruff, process-group
integration, actual preparation/start, CUDA continuation and recorded-prefix
checks pass. V95 still needs its full20k endpoint, then complete matched quality
evaluation and actual native crop review. V43 remains the working reference;
speed work stays deferred and the full PROMPT objective remains unproven.

