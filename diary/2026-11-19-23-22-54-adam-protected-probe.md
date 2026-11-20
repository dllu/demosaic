# Qualify finite AdamW step protection

Recorded: 2026-11-19T23:22:54-08:00 (America/Los_Angeles).

Started independent finite shadow updates from the completed regional
raw checkpoint and optimizer state. The active-set projection agrees
with a separate constrained solver on 240 cases. The first shared and
full steps exactly match PyTorch fused AdamW's parameters, optimizer
moments and clocks. Verified the first eight source pairs and archived
their observations and readouts.
[Probe method and evidence](../docs/local-adam-protected.md).

The full collection uses 32 paired regimes with a separate photo for
each update. It compares the protected step with a norm-matched
unprotected step. The canonical endpoint photo panel runs separately.
[Parent endpoint and native comparisons](../docs/local-regional-wire-1024.md).
