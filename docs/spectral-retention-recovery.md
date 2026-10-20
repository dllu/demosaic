# Spectral trial: repair checkpoint retention without resetting training

The control has resumed from its verified1,000-update checkpoint and passed
logged update1,025 in the published observation. Corrected CPU/CUDA and external
resume checks pass. Final model quality has not been evaluated. V43 remains the
working reference. [Complete recovery evidence](results/spectral-retention-recovery-v1.json).

The first resumed controller later stopped at a resource bound. The
[explicit operational reserve recovery](spectral-resource-recovery.md) records
the failure and current run, preserving the original1000 checkpoint and4000
horizon. The owner/root information below is the earlier dated observation.

## Fault and correction

The trainer saves `last.pt` during its final scheduled validation and again when
`stop_after` reaches the same boundary. My new trial wrapper incorrectly required
the retained `step-004000.pt` copy to be absent on every save. It would reject
the second identical save after completing the original4,000 updates. The
16-update engineering runs did not exercise retention at the4,000 boundary.

The corrected wrapper accepts an existing retained copy only when its SHA256
matches the new checkpoint. Different bytes still raise an error and preserve
both files. A regression test uses the real PyTorch checkpoint writer at4000,
saves twice, and verifies that a changed model cannot overwrite retained bytes.
No model, loss, data, noise, numerical precision or optimization code changes.
All46 training-core modules remain identical to the original frozen trial.

## Controlled handoff

A separate CPU watcher waited for the immutable retained1000 copy to match
`last.pt`, checked all91 model/91 EMA/89 AdamW states for finite values, counters
1000 and nonnegative second moments, and copied the complete checkpoint.
Its SHA256 is
`2388c26b26767f0dd60c466b385bdaa93c7ca52543e1639310540898c184ab9c`.
All56 recorded source/actual-forward/actual-loss observations and the metric
prefix through1000 are retained. Original logs, files, plan and code remain intact.

Only exact owned sessions533083/1792461642.08 and533376/1792461711.09 were
stopped, controller first. Both creation identities and exits were checked.
Some unretained work after1000 may be discarded; it is not represented as part
of the retained trajectory. The original status file remains a historical
observation; the completed handoff receipt records the deliberate exits.

The replacement resumes the full model/EMA/AdamW/RNG state at1000, performs
only the remaining3,000 updates, and starts the spectral arm from the original
V63 EMA for its original4,000 updates. Warmup and cosine retain the original
4000 horizon. The control's active timeout retains only its unused13,462 seconds
of the original14,400, after938 consumed seconds. There is no budget extension,
optimizer reset, checkpoint selection or held-out-driven change.

## Recovery evidence and remaining review

Corrected CPU and CUDA preflights use genuine B1/native64/FP32 and
B16/native256/BF16 control16, spectral16 and8+8 restart runs. A separate fresh
CPU process resumes an external step8 checkpoint
and saved observation/metric prefix; its final model, EMA, AdamW, counters, best
bookkeeping and Python/CPU/CUDA RNG exactly match uninterrupted16. All16
observations match. This validates the recovery adapter without a quality or
cross-device numerical-equivalence claim.

All six original-versus-corrected CPU/CUDA endpoint pairs have bitwise-equal
model/EMA/AdamW/RNG/best/step/model-configuration states and identical saved
observations. A separate tiny CUDA serialization fixture also passes repeated
retention with an interleaved `best.pt` save and rejects a changed state. Its4000
checkpoint label exercises the writer; the fixture performs only one optimizer
update and is not a4000-update training result.

The new source-frozen recovery contains288 files/796 input bindings, plan SHA256
`459509319574527cd651b0905a04b99613eec5089899bfd6b8d05999800b20dc`.
The actual start header records step1000, original horizon4000,88,508 Commons
sources,106 native groups and32 paired scenes. The first resumed forward matches
all saved model tensors exactly; the recorded official DINO hash stays unchanged.
The published observation reaches1025 and preserves all56 prefix observations.
The same
source/noise/loss/base-LR observation checks, final RNG comparison and original
[full quality/native criteria](spectral-v88-v89.md) remain required. Reports keep
two native exact-GT triplets per endpoint and the standing cached GFX3879/3880
sky/building/foliage/fence/highlight views, accurately labeling ISO100 as an
independent different-aperture/time reference. There is no automatic promotion
or new full-frame/speed result.

Current training root:
`/mnt/external/demosaic/experiments/spectral-v88-v89-retention-recovery-v1/`.
Controller544254/1792462947.40 and control worker544572/1792463016.96 were exact
live owners at observation. The spectral arm is queued in that controller.
Inspect current handles/status rather than treating this dated observation as
proof of later completion. Original artifacts remain under the original4k root.
