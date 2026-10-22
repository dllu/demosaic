# Adopt V84 and refresh current model documentation

Recorded: 2026-10-22T10:37:04-07:00 (America/Los_Angeles).

The user clarified that choosing V43 again had followed misleading current
documentation and overly restrictive promotion rules. Adopted V84 final20k as
the preferred quality and architectural baseline, with V85 a close alternative.
On the existing full photographic panel V84 scores 36.43996 dB versus V43's
34.89934 dB, a gain of 1.54061 dB. Unseen-camera CFA improves; known-camera CFA
is slightly lower. The existing bright-magenta comparison shows improvement
over their V63 parent. These are useful checkpoints even though the original
22-capture experiment did not meet every declared study gate.

Updated README, current model guide, GFX comparisons, requirements, experiment
navigation and training plan to describe current recommendations. Scoped stale
V43 declarations in versioned reports to their historical study, preserving
the original text locally and all immutable numerical receipts. AGENTS.md now
records the distinction between current documentation and chronological diary.
Regenerated the PSNR figure with V84 highlighted; all 39 original points and
18 source records are unchanged. Viewed the updated figure and both galleries
at original resolution. The comparison boards contain 36 unchanged native
160×160 cells, backed by 24 shipped triplets and complete source/ROI/checkpoint,
conditioning and display metadata. GFX includes sky, building, foliage and
chain-link fence. Its independently captured ISO100 image remains a qualitative
reference. One historical V95 sky noisy-preview channel differs by 1 RGB8 level;
the gallery records that difference without changing prediction/reference pixels.

Cached an exact copy of the original V84 checkpoint at
`/mnt/external/demosaic/models/v84-original20000.pt`, SHA256
`134887e12357aabf420cceee3ee53fc8832cf02a8f81ff883b829a9e51e16f10`.
Current and archived loaders preserve all 91 final EMA tensors and the frozen
DINO identity; their CPU64 outputs are bit-exact. This is a compatibility check,
not a new quality or full-frame timing measurement.

Prepared V100/V101 continuations from that exact V84 EMA, using fresh AdamW,
the curated 88,484-source Commons cohort and V84's broad flat-color palette.
Both run 10,000 updates at B16/native256 with seed59 and LR3e-6. V100 preserves
the original optical PSFs; V101 removes them, adds weak synthetic detail and
photographic contrast attenuation, and samples the six reviewed photographic
ROIs at 5% conditional probability. This tests the complete fine-detail recipe,
not an isolated component. The original V84 cohort already had 84,867 Commons
sources, so the change includes targeted quality review and a modest increase.

The first CUDA smoke stopped before optimizer updates because deterministic
cuBLAS workspace configuration was absent. Preserved that failed namespace,
set `CUBLAS_WORKSPACE_CONFIG=:4096:8` and launched a fresh source-frozen v2 study.
Both recipes then completed eight actual updates on CPU64/B1 and CUDA256/B16,
with exact initial EMA/DINO and finite model/optimizer checks. V100 production
is live, observed at step 1500; V101 is queued. No production quality result is
available yet. The runner checks RAM/disk headroom and manages only its owned
workers. Frozen plan:
`.cache/current-quality-20261022-v1/training-v2/plan.json`, SHA256
`1fdfdd8cae7d1a784faeb2442d9b8a808c64e8131ea045d4f68b5958b78b941c`.

[Selection and launch evidence](../docs/results/current-model-baseline-selection-v1.json)
binds the original evaluation, model, compatibility checks, gallery, document
role changes and training launch. A second pass scoped 40 further multiline
V43 declarations to their original studies; previous bytes and the revision
chain are retained in
`.cache/current-quality-20261022-v1/documentation-role-updates-v2.json`.
No SOTA, broad real-camera superiority or new
V84 full-frame timing claim is made. Quality and native crop comparisons will
guide the next recommendation; one study-specific gate will not freeze it.
