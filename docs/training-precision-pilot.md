# V130: matched FP32 training pilot

**V130 tests IEEE FP32 training against the completed V129 BF16 control.
Quality is unmeasured.** The [fixed-weight diagnostic](training-precision-gradients.md)
shows a large gradient discrepancy on one faint ADC training example and mixed
results elsewhere. The [completed V129 data pilot](reviewed-detail-training-pilot.md)
shows no useful visible gain at1,000 updates. Both observations motivate a
precision-only trial, without changing the recommended V120 weights.

[Recipe](../configs/quality-v120-fp32-pilot-v130.yaml) ·
[Source-frozen runner](../scripts/train_precision_pilot.py).

Only compute precision changes. Both start freshly from V120's20,000-step EMA,
with seed70,90,782 sources/27 regions, reviewed-region quota.5, native256/B16,
single noise view, zero optical blur, paired32/native128, LR1e−5 and100 warmup
steps. Feature/shadow/band/conditional-mean terms stay off. All1,000 source,
clean-tensor and noisy-tensor hashes must match V129; domain counts remain
477 Commons/262 native/261 paired. Both endpoints will be evaluated in FP32.

The existing CPU128/B1 check already forced FP32 for V129. V130 adopts that
unchanged18-update receipt only after proving equality of the complete effective
CPU configuration and every training-source file. Only output paths, notes and
paths to byte-identical validation protocols differ. This saves repeated neural
work; the original receipt still correctly identifies V129.

New CUDA256/B16 checking runs16 updates, validates rejected changed shadow
settings before model construction, then resumes the actual checkpoint for two
more updates. Fresh production has a separate1,000-update budget. Admission is
52GiB available RAM, the CUDA cap is16GiB and runtime floor32GB; deadlines are
30minutes for the check and8hours for production. No automatic retry or budget
reset is allowed. Actual finite states, input identities and resource use are
recorded by the worker; a B1 diagnostic does not qualify B16 memory.

The actual CUDA16+2 check has passed: all18 clean/noisy batch hashes match V129,
91 model/EMA tensors and89 Adam states are finite, and the preserved16-step
checkpoint resumes exactly. Peak CUDA allocation is11,332,900,352 bytes.
[Actual check and CPU-adoption receipts](results/v130-implementation-checks-v1.json).
Fresh production is now running; its quality remains unmeasured.

Training plan/status:
`.cache/current-quality-20261023-v1/fp32-training-pilot-v1/run/`.
Quality queue:
`.cache/current-quality-20261023-v1/fp32-quality-pilot-v1/queue-v2/`.
The86-call retained-input quality panel covers ordinary/shadow high-noise
materials and both real GFX scenes, with saved V129/V120 controls. The separate
[faint photographic ADC panel](faint-adc-precision.md) now has32 of48 declared
predictions:16 each for V120/V129, with V130's16 queued on the same inputs.
Preparation, baseline scoring, source strata and native/display audits pass;
V129 has small mixed changes. Neither panel establishes FP32-trained quality
before the actual V130 endpoint. Native review and independent reductions remain
required for interpreting that result.
