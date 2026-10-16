# Isolate the low-noise color bias and evaluate a narrow intervention

The third diagnostic uses original batch companions/positions. All56 Malvar
cases match exactly against each canonical suite. Neural maximum differences
remain .001793/.001431 for first1000/step2000, so strict1e-4 replay flags remain
false. The residual discrepancy is not fully isolated. Do not replace canonical
scores or interpret tiny effects. Earlier failed attempts/logs remain intact.

The multi-dB findings are clear on these selected patterns. Zeroing only learned
WB/matrix columns raises synthetic-13 ADC PSNR26.063→40.015 and ISO100
26.965→41.550; source0 rises30.500→35.351 and31.367→36.638. The visible failure
is a broad color bias. Removing physical anchors/masks harms the cases and
DINO-off is mixed, losing about5dB at high noise. These are inference
interventions on selected failures, not trained ablations or global gains.

[Diagnosis](../docs/native-low-noise-camera-diagnosis.md),
[all504 cases and16 verified native triplets](../docs/results/native-low-noise-camera-diagnosis-v1.json).
Noisy/GT panel bytes and physical settings match across all eight methods.

Inference-only V46 zeros exactly one slice of immutable V43 step2000 EMA:
`pretrained_rgb.measurement_adapter.weight[:,9:21]`. Every other tensor and the
first9 columns remain exact after serialization. Physical WB/matrix, CFA,
anchors and DINO remain active. Zero new training updates. Export SHA
`b0b4be3d83d69e1f20459d972b72a0fe13ffff9f4ad903024ea89b6a790c9c68`.
Receipt `/mnt/external/demosaic/runs/camera-projection-off-v46/receipt.json`.
Both drivers are archived beside it under runs.

Controller PID1109184 completed measurement at08:34:00UTC and exited: known/
unseen,427-photo/16-procedural and full102MP GFX. Two new RGB16 outputs verify
SHA/size/dtype/shape/bitdepth/samplecodes/ICC. Photo mean34.94790/.956582 and
procedural34.23655/.968622. Known primary54.07672 and unseen53.74494 are lower
than parent54.23332/53.80606. Do not promote from selected-pattern results.

Outputs under evaluation: `paired-{known,unseen}-camera-projection-off-v46`,
`synthetic-camera-projection-off-v46-full427`,
`gfx-3879-3880-camera-projection-off-v46-full`.
Terminal status `/mnt/external/demosaic/runs/camera-projection-off-v46-workflow.json`.

Next: combine cached V43 first1000/step2000 with V46 only after strict protocol/
classical-case parity; publish ten new native triplets and inspect GFX. Keep
current reference until reviewed. Choose a focused training repair afterward.
Training from this inference export alone would let the zeroed columns learn
again; a permanent omission needs an explicit feature mask or frozen slice.
Finer WB versus matrix/constant-bias probes may retain useful real-camera
conditioning. V44/V45 and LoRA quality trials remain untrained; objective unmet.
