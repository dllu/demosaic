# Bounded RAW/residual-unit CUDA test

Completed four fresh IEEE FP32 CUDA arms on the same16 frozen training-only
batches. Each starts with identical seed51 weights and exact bilinear outputs,
runs256 updates, and discards learned weights. Compared raw, input gain32,
known-noise input companding and gain32 with the learned residual divided by32.
Physical RAW skip, output/loss units and capacity remain unchanged.

Residual scaling reduces early loss overshoot. Final original-loss ratios to
the common start are.97615/.99937/.99581 for Commons/native/paired, compared
with1.07826/1.22989/1.36577 for raw. Native/paired gains are tiny, paired MSE
remains above its start, and input gain alone improves Commons/native MSE more.
No production adoption, quality claim or convergence verdict follows.

All nine focused tests and Ruff pass. Independent replay verifies1024 ordered
finite training records,96 domain means,27 inputs and45 guards. All852 Adam
states per arm are finite at256, all fixture fingerprints remain unchanged and
the exact process exited. The separate CPU study continues unchanged.

Published the diagnostic script, tests, report and numerical evidence. The next
focused question is whether removing a fixed local low-frequency component from
RAW input features makes noise/detail easier to learn at these residual units.
That would be a separate discarded experiment, not a production change.
