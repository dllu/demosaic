# Complete the current-data batch sweep and DINO adapter GPU checks

The previous goal turn made progress: the corpus second gate,30 native triplets,
six full RGB16 outputs and reviewed README/reference selection were published
and pushed. This turn revalidated both owned queue processes, then observed their
terminal success and exit. No owned GPU work overlapped either workflow.

The actual4× Commons/native128 sweep completes all ten cases. Mean native256px
patches/s: batch4 27.47,8 29.65,16 30.81,32 31.21,64 30.76. Batch16 is12.1%
above4;32 is only1.3% above16 with13.41GB versus6.95GB peak CUDA allocation.
Keep batch16 fixed in controlled quality comparisons. All ten runtime recipes
verify the same initialization, source, model and data/augmentation settings.
The sweep is not image-quality or convergence evidence.
[Measurements and scope](../docs/current-pipeline-batch-sweep.md),
[complete receipt](../docs/results/training-batch-sweep-v2.json).

GPU-check queue PID1086009 subsequently completes in frozen codeca846a0.
All352 CUDA-enabled tests pass in30.78s. Genuine full-model rank4 adapters retain
exact initial outputs in BF16 and FP16 for all four CFAs, with FP32 output.
Adapter gradients are finite/nonzero; original foundation tensors remain
unchanged. A complete two-update checkpoint resumes to four with AdamW step
counters retained; all48 new learned matrices persist and EMA reloads exactly.
The CPU test separately verifies uninterrupted/resumed model/EMA/optimizer/RNG
equivalence. These small fixtures establish execution, not quality or full-batch
memory/throughput. [GPU receipt](../docs/results/dino-lora-gpu-preflight-v1.json).

After both workflows exited, launch selected failure diagnostics in the original
V43 code. The original strict1e-4 neural replay assertion failed: the first tiny
discrepancy was.00013dB. Matching source positions alone still gives small neural
differences up to.00363dB in the captured second attempt. All56 classical cases
match exactly against each original suite, so observations/render/metrics match.
Failed attempts/logs remain intact. No main-suite quality number is replaced.

The captured probes show large projection sensitivity: zeroing the complete
measurement projection recovers about8.69dB on synthetic-13 ADC-only and4.59dB
on synthetic-0. DINO-off is mixed and harms high-noise performance. These are
inference distribution changes, not causal trained ablations or selected models.

The third diagnostic now uses exact original batch companions and positions,
retains every strict-replay difference explicitly, and separates CFA values,
CFA masks, photometry anchors and camera metadata. Live PID1106656;
log `.cache/public-native-expansion-worktree/.cache/native-low-noise-diagnosis-v3.log`.
Output `/mnt/external/demosaic/evaluation/native-v43-2k-low-noise-diagnosis-v3/`.
The executed driver is archived beside that output as
`diagnose_native_2k_low_noise_v3.py`. It preserves native160px exact-GT triplets
and original checkpoint/effective-weight hashes for every override. No further
quality training starts until the low-noise failure is understood.

Next: inspect the completed group diagnostic, publish its verified evidence and
choose a focused repair with a matched training control. Current V43 step2000
remains the photographic experimental reference with its reported tradeoffs.
The original objective, trained DINO attribution, protected-final quality and
10-second target remain unproven.
