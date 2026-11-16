# Full-model RAW-attention comparison: control complete, spatial arm training

The existing V131/V132 comparison has a new, separately recorded execution.
**V131 completed20k on November16; V132 is training from V120 EMA.**
The original failed controller, RAM-stop receipt, checkpoint and source remain
intact. V131's [targeted102-input/native review](v131-endpoint-quality.md) is
complete: faint-ADC +0.14555 dB across four sources, with a bark regression,
small ordinary/shadow gains and no clear new fine cab crossings. V120 remains
the general recommendation; V132 endpoint quality is unmeasured.

This addresses the broader comparison in the [weak-detail research review](weak-detail-literature-2026-11.md):
small residual heads do not bound what a trained restoration trunk can recover.
The [complementary branch](complementary-edge-response.md) retains a small
lower-noise conditional gain, while real mesh, building color and flat failures
persist. An already implemented [RAW spatial-attention branch](raw-spatial-features.md)
offers the original full-horizon comparison. The separate
[V144/V145 1k pilot](v144-v145-quality.md) already found no useful new detail
gain from this branch with a V143 parent and larger branch learning rate.
This continuation does not assume that longer training will fix that failure.

## Preserve the scientific recipe and completed work

The original [matched plan and four CPU/CUDA checks](raw-spatial-training.md)
remain binding: cleaned90,781 Commons sources/29 regions,32 paired scenes,
106 training native-RAW scenes, seed70, native256/B16/BF16, one noise view,
single-view Charbonnier loss, zero optical PSF, reviewed-region quota0.5,
LR1e−5/warmup100/cosine20,000. Only `raw_spatial_features` differs between arms.
All protected GFX captures/JPEGs/siblings remain outside training.

| Arm | Preserved work | New execution |
| --- | --- | --- |
| V131 control |14,549 updates,448 validation forwards, all clean/noisy hashes | Completed remaining5,451 updates/192 validation forwards, no replay |
| V132 RAW attention | Discarded16+2 CPU and16+2 CUDA checks | Fresh20,000-update/640-validation production running from V120 EMA |

The additional branch has signed CFA differences and two window-attention blocks
with shifted support, feeding the existing restoration trunk. Both arms train
the full restoration path; DINOv3 stays frozen. V131 has91 restoration tensors/
89 Adam states; V132 has114/112. All23 added tensors had finite nonzero gradients
in the original exact-recipe checks. V132 must match all20,000 control clean/noisy
hashes and the original first initial outputs, including its first18 smoke inputs.

This preserves each original20k horizon and avoids replaying the14,549-step
control prefix or the completed checks. It is a new explicit execution after
the original queue terminated, not an alteration of the old failure record.

## Executed adoption checks

All106 original input/source checksum checks pass. The original checkpoint loads
with matching installed/saved PyTorch2.14.1+cu130 and deterministic backend
settings. Its model, EMA, Adam and Torch/Python/CUDA RNG are present and finite;
all89 Adam clocks equal14,549. The full14,549 input trace and forward/update/
target counts agree. Original training owners are dead; V132 has no production
claim. The checkpoint is copied unchanged into the new namespace, SHA256:
`ddbb4d6fbec2f76c2b79abb60c9afcbb1cf7ca32380b9ee73e51e94ee8983716`.

Actual resumed training verifies all91 model tensors before its first forward,
all89 Adam states and parameter groups on restoration, and CPU/Python/CUDA RNG
before the first new noise draw. Step14,550 uses LR
`2.5653477379816604e−6`, the correct position in the original20k schedule.
The earlier adoption publication captured14,724 updates with input14,725 next.
The completed control now has all20,000 Adam clocks/updates,640 validation and
20,640 encoder calls/320,000 target contexts. Its checkpoint SHA256 is
`4d78e6302f6e72d68acb03fe58eb7106763b8129ccb059747ef5d2cfbd3ec1e1`.
V132 production started only after control completion and has retained its
immutable1,000-step snapshot within the same20k worker/schedule.
Its [matched progress review](v132-progress1000-quality.md) is complete: all1,000
training input hashes agree,102 retained inputs/all64 native and eight amplified
boards are reviewed. Faint ADC is+0.03356 dB versus V1311k and−0.23979 dB versus
V120, without clear new real mesh crossings. This remains an early comparison.

The complete original numerical/data package is copied byte-for-byte under the
new `work` directory; only output run paths change in the recipes. The source
hash remains `360c8d1b6256de562cc9cfce36ea9e3d0ff1467afac786ffba6c9b0af2ea9160`.
All new artifacts/caches are internal. External datasets/manifests remain read-only.
The new execution uses52GiB RAM admission,16GiB CUDA allocator cap, the original
32GB runtime memory floor, two CPU threads/low priority and48h per launched
worker. Internal free-space admission/reserve is128/96GiB. External read-only
admission/reserve is96/64GiB, replacing the historical208GiB write reserve.
No other job is signalled; no automatic retry is performed.

The first new launcher placed outputs outside the original frozen package's
allowed directory. It stopped before model construction, new noise or updates.
That complete failed prefix is preserved. The corrected execution copies the
package and places outputs inside its permitted directory; the actual copied
safety function accepts both run paths and rejects an outside-work path.

[Runner](../scripts/resume_raw_spatial_trial.py) ·
[Thirteen focused state/trace/relaunch tests](../tests/test_raw_spatial_continuation.py) ·
[Exact adoption, source, first-update and failure evidence](results/raw-spatial-continuation-v1/publication.json).

The [matched endpoint detail review](raw-spatial-endpoint-review.md) runs per endpoint
with exact source/state/input checks, explicit camera-JPEG cells and an independent
CPU metric/native-pixel audit. It reuses the original102-input panel and saved
V120 predictions. V131's collection/audit/all64 native-board views are complete;
V132 will compare with the saved V131 endpoint without another control forward.

The separate broad numerical/full-frame review remains required. It must retain
ordinary photos, faint/ADC/flat controls, at least two native noisy/restored/GT
triplets and both protected real-photo families with accurately labeled
independent references. The targeted gains/costs are documented now, while the
broader427-photo/camera/flat/full-frame review and architecture comparison remain pending.
