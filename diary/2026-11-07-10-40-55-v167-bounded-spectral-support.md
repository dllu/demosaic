# V167 bounded spectral support

Recorded: 2026-11-07T10:40:55-08:00 (America/Los_Angeles).

V166 improved quiet color bias but its spectral support still nearly closed. V167 isolates an architectural constraint: support=f+(1-f)sigmoid(logit+log(1-2f)),with f=.25. Both initial support values remain.5 and initial outputs equal the parent. Frequency gains can still vanish and direct RGB can cancel;this does not guarantee delivered detail or safe noisy flats. The new mapping changes the logit derivative at zero from1/4 to1/6.

All266 CPU checks pass,including28 new independent mapping/adjoint,bounds,initializer,RNG/state,zero-floor whole-head output/auxiliary/parameter-gradient compatibility across allCFAs,and zero-variance constant-RAW checks. All89 prior neural source files stay byte-identical;one isolated new module retains124909 parameters/47 tensors. Per-arm constructor metadata explicitly records support_floor in checkpoints and exports. GPU parity passes28 archived contexts/allCFAs/native256/384/512/768:56root calls.24 CUDA scalar/leaf checks pass. Genuine8+2 save/reload/continuation smoke passes with94 finite Adam states and nonzero prefix gradient maxima for all94 parameter tensors.

Both heads retain the V166 routed-common loss recipe,data,initial weights,LR,AdamW,clipping and EMA. Candidate bounded support is the only architectural change. The control must reproduce all1000 V166 trace/raw/EMA/Adam and1644 actual predictions. The original controller and full822-case/four-endpoint review queue are live with a fixed1000-update horizon. Support min/mean/max and declared floor are recorded and bounds checked on every smoke/train/review forward. The first40 actual control rows and80 FP32 weighted losses/support bounds were checked before publishing readiness. Final quality remains pending.

[Protocol](../docs/bounded-spectral-support.md) · [Archived motivation and CPU evidence](../docs/results/v167-bounded-support-motivation-v1.json) · [Immutable readiness](../docs/results/v167-bounded-support-preparation-v1.json). Expected5364 scientific roots/11424 head images,24CUDA leaf checks separate. No new parent/DINO/source/sensor-noise/RAW/dataz calls. All protected scenes,siblings,JPEGs and18held-out source IDs remain excluded. Prior receipts and evidence are preserved. The user's fine dark detail and flat-region objective remains unresolved.

