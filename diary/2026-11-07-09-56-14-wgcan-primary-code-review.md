# WGCAN primary code review

Recorded: 2026-11-07T09:56:14-08:00 (America/Los_Angeles).

Reviewed WGCAN's July2026 publisher abstract/section snippets and separately inspected four author files at commit87413dd280af8228f34fe33188136077ad81ca68 through the connected GitHub tool. The publisher full page returned403. Do not claim a full-paper review or reproduction.

The actual one-level Haar objective sums meanL1 over LL/LH/HL/HH, including low frequencies. Training combines RAW/RGB/wavelet0.7/0.2/0.1 after RGB clipping; validation loss uses0.5/0.4/0.1. A helper's Euclidean label is misleading; its operation is L1. These details matter before transferring loss weights to our linear camera-RGB/physical-noise task. The repository has no declared license; no source, weights or data were adopted or executed. The fixed V166 trial remains live and unchanged.

[Pinned primary file hashes and exact reading scope](../docs/results/wgcan-reading-20261107-v1.json) · [Research discussion](../docs/research.md#inspecting-a-recent-wavelet-objective).

