# Local RAW contrast and equal-example batch learning

Completed the fixed local7/local31 mean-subtraction CUDA test. All arms share
identical fresh weights, initial bilinear predictions and residual÷32. Local7
improves native original loss by2.29% over initialization and paired by.71%,
but MSE gains are small and Commons loss/MSE trail input gain32. No single arm
is best across domains and metrics; no production adoption follows. All weights
are discarded. Eight tests pass; independent replay verifies1024 ordered rows,
96 means,33 inputs and46 guards. Exact GPU owner exited.

Prepared and launched a separate four-arm batch4/batch16 learning comparison
for raw and gain32/residual÷32. Every arm consumes4096 identical ordered example
draws. Real batch16 joins four B4 input groups, retains their original domain
loss reductions and averages before one update. Batch4 makes four updates.
Fixed LR/decay per update and unequal update counts are explicit; this is not
an optimized batch16 recipe or a throughput claim.

Four tests verify physical batch16 gradients/losses against four B4 accumulated
calculations with nonzero heads, mixed domains and all CFAs, plus single-group
equivalence, state/input preservation and invalid groups. Ruff passes. Frozen
plan guards40 inputs and46 files, starts after preceding GPU owners exit and
exports no learned weights. No quality or convergence claim is made. The CPU
coordinate diagnosis continues without modification.
