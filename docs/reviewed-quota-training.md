# V133: broader photographic sampling at a matched budget

**V133 tests a 5% reviewed-region quota against V131's 50%, with the same V120
Small architecture, parent, dataset and 20k schedule.** Both device checks are
complete. Production is queued after both original spatial arms finish; trained
quality is unmeasured. V131 is reused as the control without old training or
inference replay. V120 remains the general recommendation.

The [source-schedule audit](training-source-schedule-coverage.md) motivates this
comparison: the lower quota would visit 62,872 rather than 42,086 of the same
90,781 photographic sources in 20k planned updates. These counts establish
broader source exposure; restored quality remains to be measured.

[Recipe](../configs/quality-v120-reviewed-quota-v133.yaml) ·
[Runner](../scripts/train_reviewed_quota_trial.py) ·
[Checks, source correction and live owners](results/reviewed-quota-training-setup-v1.json).

## Controlled recipe

| Setting | V131 control and V133 |
| --- | --- |
| Architecture / parent | V120 Small, official frozen DINOv3 pyramid; V120 completed 20k EMA SHA256 `a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb` |
| Data |90,781 Commons photos /29 reviewed regions; paired32 and native 128 manifests,106 native training scenes |
| Preparation |4× → geometry → area2, zero optical PSFs; photographic contrast attenuation.25 |
| Training | Seed70, native 256/B16/BF16, one sensor view; existing reconstruction loss; shadow/feature/band/conditional-mean additions off |
| Schedule |20,000 fresh updates, LR1e−5 /100 warmup /cosine horizon20,000;640 validation and 20,640 encoder calls;320,000 clean slots |
| Only treatment | Photographic reviewed-region quota.5 → .05 |

The newer prepared 90780/31 dataset stays separate to isolate the quota and reuse
the original V131 control. Combined data improvements should use the best useful
measured architecture as that evidence becomes available.

Every native/paired clean and noisy batch must match V131. The saved-input check
also compares wholly unaffected Commons batches and, for the first 18 steps,
all prepared tensor values of unaffected examples within mixed batches. Changed
Commons selections are expected; the two full input traces should not be claimed
identical. Domain batches remain 10,046 Commons /4,965 native /4,989 paired.

## Executed checks and resume fix

CPU128/B1 and CUDA256/B16 each complete 16 updates and two resumed updates.
Across both,262 unaffected examples match 141,054,572 saved prepared values
exactly against V131. Both stages preserve 91 model/EMA tensors and 89 Adam states,
finite at 18, with the official encoder frozen. CUDA peak allocation is
7,041,804,800 bytes; these are implementation checks, without a throughput claim.

The first CPU check exposed a validation-order bug: a changed reviewed quota
reached the construction hook before the late compatibility check. It stopped
before constructing that rejected model or running a rejected forward. The
16-step state and failure remain intact. The pure ROI compatibility check now
runs before construction; actual changed quota and changed catalogue resumes
both reject there. Only the remaining two CPU updates were executed, within
the original absolute 30-minute deadline and 20k LR horizon.

All 62 other training modules match the control bytes. Reversing the single
guard relocation restores the entire original `train.py` byte-for-byte; successful
training arithmetic is unchanged. Independent constructor-free inspection checks
526,475,668 saved model/EMA/Adam values across all four actual16/18 checkpoints.
Original failed-controller, source and machine-receipt bytes remain intact.
[Local-time history](../diary/2026-10-27-09-36-16-reviewed-quota-training.md).

Total discarded budget remains 36 training/optimizer/encoder calls and 306 clean
slots. The CPU prefix is adopted rather than repeated. The controller waits for
the exact original V131/V132 controller to complete both arms and exit before
production. Limits are 52GiB launch headroom,16GiB CUDA allocation,32GB runtime
floor,48h per production worker and an eight-day dependency wait. Original mean
and spatial jobs retain their owners, inputs, schedules and budgets.

## Retained progress review

The same 20k worker retains its 1,000-step checkpoint without stopping or restarting
the schedule. A live queue plans 102 new IEEE-FP32 V133 calls:64 saved shadow
observations,16 ordinary material cases, four main GFX512 contexts, two extra
mesh768 fixed profiles and 16 faint-ADC observations. Saved V120 and original
V131 progress predictions are reused. The original 102-input preflight is adopted
after exact observation and source-compatibility checks.

Control adoption checks arrays, fingerprints, target/reference, ROI, exposure
and noise metadata. CPU reports and independent FFT/native-pixel audits follow.
Reports prepare at least two unchanged native 100% noisy/restored/exact-synthetic-GT
triplets, plus both real GFX scenes. Separate DSCF3880/DSCF3835 ISO100 and camera
JPEG references remain qualitative, not GT; aperture, exposure time and moving
subjects differ.

## Full endpoint review

Four live queues now wait for the exact completed 20k training owner: endpoint
collection, independent CPU audit, saved-output comparisons and the extra mesh.
[Full-review setup and constructor-free preflight](results/reviewed-quota-full-review-setup-v1.json).
The genuine 18-step candidate was tested and rejected before neural construction;
no full V133 endpoint or quality result is available yet.

| Collection | Planned V133 root/encoder calls | Retained observations |
| --- | ---: | ---: |
|427 photos and 16 procedural targets |3,108 |12,404 |
| Known / unseen measured cameras |24 /30 |72 /90 |
| Texture / color probes |112 /1,176 |448 /1,176 |
| Main GFX / highlights |4 /2 |4 /2 |
| Complete 102MP GFX,520 tiles |130 |520 |
| Extra fine mesh, two fixed profiles |2 |Both native 160 regions/profile |

This is 4,586 full-panel calls plus two mesh calls; the already queued 102-call
progress review is separate. Numerical inputs match the original saved
witnesses. The CPU audit will check 14,190 numerical observations, and comparisons
will cover all 427 photos' local detail, two native exact-synthetic-GT triplets and
all six main GFX regions. Complete linear/sRGB RGB16 exports will be verified.

V120/V117 results are reused. V131 will be resolved after its original independent
audit completes, by owner, plan and checkpoint identity, without a control rerun.
The quota-only V131/V133 full-frame contrast requires matching noise conditioning,
the same 32-pixel grid and identical actual inputs for all 130 tile batches.
Older V120/V117 profiles/grids retain their explicit comparison limitations.

The mesh queue will reuse nine controls, including existing V120 predictions and
V131's original predictions once available. Only V133 gets two new CPU FP32 forwards.
V120/V131/V133 native boards and triplets will share both ROIs and +4EV; the ISO100
reference remains nonexact. Model quality and actual native viewing are pending.
Useful measured gains should update current recommendations and galleries with
their remaining weaknesses, without a historical promotion threshold freezing
the baseline. These finite reviews do not establish broad real-camera superiority
or SOTA by themselves.
