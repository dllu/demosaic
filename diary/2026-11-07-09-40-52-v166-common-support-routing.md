# V166 common-loss support routing

Recorded: 2026-11-07T09:40:52-08:00 (America/Los_Angeles).


V166 isolates a training-only common-loss derivative: hold the actual local support activation fixed for this term while retaining direct spectral and spatial RGB derivatives. Inference, numerical loss values, all weights, data, initialization and optimizer match V165. Other losses still train support. The proposed derivative is deliberately a surrogate, not a finite-difference gradient. The four-call saved-checkpoint diagnostic and 17 new CPU checks pass; the relevant suite passes 238 checks. All 376 saved parameter-gradient arrays were replayed independently. See [protocol and motivation](../docs/common-support-routing.md).

The first smoke run failed in newly added telemetry: complex spectral coefficients were squared without taking magnitude, then converted to float. One complete paired-arm row and the second control update completed; three actual root calls are retained in accounting. No checkpoint or full training existed. All original owners were checked terminal. Preserve original v1 sources, receipts and logs. Corrected v2 paths use magnitude RMS and adopt the completed 56-forward/20-leaf parity receipt without repetition. A new smoke is necessary because no restorable checkpoint exists. [Correction receipt](../docs/results/v166-telemetry-correction-v2.json).

The corrected controller and full review queue were launched with the same fixed 1,000-step horizon, all 822 cases/four endpoints and 72 native comparisons. Quality remains pending. Expected total including probe and failed prefix: 5,371 roots / 11,452 head images; zero new parent/DINO/noise/source/RAW calls. The user’s fine-detail/flat-region objective remains unresolved.
