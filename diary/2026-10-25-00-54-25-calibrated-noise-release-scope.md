# Record calibrated noise-model release and dataset scope

Recorded: 2026-10-25T00:54:25-07:00 (America/Los_Angeles).

Reviewed the current author PNNP release as a separate possible noise/data
improvement while the original V117/V118 objective comparison runs. The
release pins commit8704a5e8852da305097618f9b1335630dcfdd889. Its source is
Apache-2.0; released sensor weights cover A7S2/IMX686, with dark-frame evidence
needed for another camera. The GFX cameras have no calibration established by
this check. Proxy-training code and separate resource-archive weight terms
remain unavailable/unverified in this inspection.

Both pinned LRID dataset cards explicitly declare CC BY-NC4.0. They are outside
the project's commercially usable training-data scope. Only metadata/cards/
source-license text were retrieved: no dataset images, weights, neural calls,
optimizer updates or RAW decodes. The AIM2025 report motivates measured-noise
work; it supplies no restoration result or camera calibration for this project.

The first generic dataset-metadata request exceeded its1MiB response bound.
Its completed GitHub response and failure receipt are preserved. A fresh v2
requests only revision/cardData, reuses the completed head response, and pins
all small resources successfully. Existing jobs, data, models and machine
receipts remain unchanged. No new training or calibration is launched.

[Research scope and primary sources](../docs/calibrated-noise-releases.md) ·
[Pinned release/card evidence](../docs/results/PNNP-release-scope-v1.json).
