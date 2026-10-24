# Check fitted Small optimizer updates and queue a matched 20k quality experiment

Recorded: 2026-10-24T02:50:46-07:00 (America/Los_Angeles).

The previous goal turn made concrete progress: it published the completed
V111/V112 material review and reclaimed 6.38GiB of duplicate immutable copies
while preserving every checkpoint path and contents. This turn revalidated
all six existing GPU handles with exact creation times. The photo evaluation
was still running, reaching 332/443 sources when the new queue was inspected.

I ran eight actual discarded CPU optimizer updates from the fitted Small
initializer on the cleaned90,864-source recipe. The checker counted eight
restoration forwards, eight Small encoder forwards and eight AdamW updates.
All 91 initial EMA tensors matched the fitted checkpoint; the other83 inherited
tensors and three nonzero learned gates remain exact to V104. The frozen
official Small encoder retained its identity and received no gradients.
Model/EMA/Adam stayed finite, and all89 fresh Adam states reached step8.
All eight actual inputs, domains, steps and learning rates matched V111's
earlier CPU check. These CPU64/B1/FP32 updates are implementation evidence,
not a quality or timing result; none will initialize production.

The new V113 recipe uses Small plus fitted transfer and the same seed62,
epsilon.001, cleaned corpus, six ROIs, zero optical blur, weak/photographic
contrast augmentation, fresh AdamW/EMA, native256/B16/BF16, LR1e-5/warmup200 and
fixed20k budget as completed V111. V111 is the trained Tiny control, avoiding
a duplicate Tiny run. The combined transfer method changes the encoder and
eight fitted lateral tensors; this does not isolate capacity alone. The
initial fit's step20000 still describes V104 history and zero new joint updates.

The source packet matches the successful CPU code exactly. I reconstructed
its source hash without neural inference; it matches the actual CPU archive
`cd35f14079462639b0fac6d9b20052b8bba395a396bcaa668383bd6575569f92`.
The numerical training/model/data/loss modules match V111's original archive;
intervening module changes concern optional evaluation/inference behavior.
Twelve protected original plans remain byte-identical.

An actual live controller, PID579485 created1792835400.68, now waits for the
exact existing GPU chain and independent audit to release CUDA. It adopts the
successful CPU check without repeating it, then runs eight discarded real
CUDA256/B16/BF16 updates. Only success starts fresh20k training from the fitted
initializer, not the smoke checkpoint. Both future stages count actual
forwards/updates and verify finite states, frozen encoder identity, source
coherence and matching logged observations. Failures remain preserved without
automatic retry/resume. No CUDA or production updates had started at recording.

[Current experiment](../docs/small-aligned-training.md) ·
[Machine receipt](../docs/results/small-aligned-training-queued-v1.json), SHA256
`601ed6c501ec91b8b6432072c17b80ba5c375141f01af92ccb5f641721c0022f`.
The new documentation describes this live queue alongside useful V111/V112
results. Trained Small quality, full panels, native crop triplets, standing GFX
and full-frame exports remain pending; no version-plot endpoint is added for
the preparation or discarded steps. The older zero-gate recipes and their
executed sources/receipts stay preserved and unlaunched.
