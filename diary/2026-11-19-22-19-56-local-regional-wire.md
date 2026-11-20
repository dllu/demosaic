# Start matched regional weak-wire supervision

Recorded: 2026-11-19T22:19:56-08:00 (America/Los_Angeles).

The next matched full-trunk comparison starts from the quieter
Local 50k EMA. Each arm has 1,024 distinct source photos split between
natural and planted wires. Both penalize weak-direction residuals
on exact absent targets. One arm uses a whole-core signed response
term and the other uses overlapping local contrasts.

The eight-update qualification is complete. The first 32 scheduled
updates have matched input fingerprints and finite gradients. The
GPU worker is running the full schedule. The local term's weight
was set from the initial output-gradient norms of three unclipped
qualification pairs. Training completion, native viewing and fixed
panel quality are pending.

[Protocol](../docs/local-regional-wire.md) ·
[Launch evidence](../docs/results/local-regional-wire-v1/launch.json) ·
[PSNR history](../docs/performance-history.md).
