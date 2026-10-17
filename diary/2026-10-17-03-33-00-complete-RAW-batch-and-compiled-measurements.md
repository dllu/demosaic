# Complete and independently check actual RAW timing experiments

The diagnosed v2 CUDA profile→RAW batch sweep→conditional compiled trial chain
has completed; all exact owners/children exited successfully. Failed v1 files
remain unchanged. No production/model/data/LR/precision settings change.

Six real batch cases, B4/B8/B16 twice: mean14.6202/15.7220/15.8103patches/s,
peak14.3063/16.6478/21.3389GB CUDA. B16 improves8.14% over B4 but only.56% over
B8; B8 uses22.0% less peak allocation. B32/48/64 twice are explicit conservative
shared-memory skips, not measurements. Each45-update measurement includes15
Commons/procedural+15native+15paired steps and all loading/augmentation/degradation/
DINO/forward/backward/AdamW/EMA work. Startup15warmup/validation/checkpoint/audit
excluded. Two runs on shared hardware are not convergence or optimum evidence.
Retain B16/LR; B8 is a future lower-memory near-tie candidate.

Independent CPU replay reads all six actual60-step checkpoints: finite94model/
94EMA/92Adam, all optimizer steps60, normalization buffers exact to initializer.
Allsource/fourdata/config/log/checkpoint hashes, LR/domain counts and Decimal
timing arithmetic pass. Actual-worker initialEMA/gradient-free actualDINO checks
remain separately identified. No training/inference is rerun by the auditor.

The actual current trace meets prespecified compile triage. Seven Inductor graphs/
121kernels execute on final10000/B4/native512/FP16neural+physicalFP32. All3,145,728
saved F32 values and whole hashes exactly match eager/prior profiler. Independent
replay verifies eight ABBA/BAAB blocks×five measured forwards, excluded switch
warmups, medians371.329/362.356ms and2.42% forward-time reduction. Both policies
retain cache, initial compile/warmup12.33s excluded. Model/DINO state and RNG stay
unchanged. Park this small process-local trial without a production option;
no new full-frame or broad quality claim. Current quality and10s targets remain
unmet; final reviewed V67 remains unpromoted.
