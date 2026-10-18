# Complete V78 original4k and verify the V79 handoff

Previous goal turn made progress by encoding the already fixed numerical review
criteria and retaining step 2,000. This turn performed verified waits on the
same actual control child 404910/1792353195.81, checking liveness by PID plus
creation time and observing finite training through the remaining schedule.
The owned watcher retained/audited step 3,000 and the final step 4,000. No
source, data, model, optimizer, schedule or quality criterion changed.

V78 completed all original 4,000 updates (64,000 example draws), passed the
worker's final engineering checks and exited. Final checkpoint SHA256:
`26e43921d2f4f46b39d9385c8399699f9fe1f0294f34efa4e6da0d4ad9baa7c4`.
All 99 model / 99 EMA / 97 AdamW states are finite, with correct counters and
shapes. All four retained boundaries preserve nonzero optimizer moments in every
new branch parameter. The control has 161 logged records and 176 sampled
legacy/input observations. Actual initial common EMA is exact and DINO remains
frozen at the official 370a84c2… SHA. The final retained hard link matches bytes.

The same controller 404904/1792353195.14 launched V79 child
444533/1792356217.53, now verified live and past its first updates. It passes the
common-parent/zero-head initialization hook. The first 16 sampled step/domain/
legacy/input/target-presence records match V78 exactly; the first full-batch hash
and common LR match too. Full 176-record and initial branch-hash/capture equality
checks remain pending until its complete result. No partial result is called a
complete matched trajectory.

Investigated a first-step loss discrepancy rather than assuming exact GPU
repeatability. Total loss delta is 0.0009739082306623459; the weighted interval
term is 0.0009720364585518838, leaving 1.8717721e-6. Logged base terms themselves
differ, mainly linear and auxiliary sensor terms. Independent FP64 summation of
the logged base terms reconstructs each total within 6.52e-10 and accounts for
the residual. Frozen training enables cuDNN autotuning, but no kernel cause is
isolated. The observed variation is consistent with the existing need to avoid
bitwise/seed-uncertainty claims; the earlier different-recipe control replay is
context, not a variance estimate for this model. Do not restart, retune or widen
the fixed criteria. Keep this caveat in eventual matched-effect interpretation.

The evaluator, CPU closure, working-reference supplement and boundary watcher
remain queued/live under their exact identities. Final quality and native crop
review waits for both original 4k checkpoints. No new improved performance,
full-frame16-bit output, speed or promotion is claimed. V43 remains the reference.
The full PROMPT objective remains active and unmet/unproven.

See [training/handoff report](../docs/directional-v78-original4k-training-handoff.md)
and [receipts](../docs/results/directional-v78-original4k-training-handoff-v1.json).
