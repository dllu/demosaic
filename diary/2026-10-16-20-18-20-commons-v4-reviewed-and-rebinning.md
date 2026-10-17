# Commons v4 reviewed 8× freeze and matching 4× launch

The previous goal turn made progress: completed the negative V61 review,
published native crops, and launched V62 with genuine preflights and queued
primary evaluation. This turn continued those exact owned processes without
restarting them.

Independently verified all 10,022 newly completed 8× caches (11,863,417,000
bytes): full SHA256, uint16/HWC shape/minimum size/recipe and exact source
metadata against the frozen 10,024-source selection. Two truncated source
failures are explicitly accounted for. All old rows and held-out assignments
remain exact; 126 protected flags remain absent, six near duplicates excluded,
and 1,018 new holdouts reserved. No protected RAW was opened or scored.

Actually viewed all three sheets/48 deterministic new-training thumbnails:
architecture/interiors, foliage, fog/sky, water/glacier, portraits/sports,
vehicles/trains, fireworks, electronics, art and stone detail. No obvious broken
decode in these resized content previews. This is not native sharpness/noise
validation or a complete scene-recognition proof.

Froze the separate reviewed 8× membership: 75,806 train, 2,303 val, 2,255 test,
including 8,872 new training sources. Manifest SHA256
05d152ef10a8f2aff7931756af54bae12c737eaad37f81c0f121eae0c5da008a.
Active model data remain at 40,170 Commons; the prior 66,934-source complete 4×
corpus remains independently usable.

Launched only the matching 8,872 new 4× caches with two CPU workers/nice5/CUDA
hidden, frozen package/operator/driver and 512GiB reserve. Controller PID
1953180/creation1792206647.0, driver
af67596c8579aad777938b34eee16e6384f85f84f8877f1923af0bb035d91e23.
Actual live startup audit saw 458 flushed rows. Twelve caches pass full SHA,
metadata/header checks and area2-to-reviewed8 comparison within one uint16
code. Full4× completion and consistency/content review remain pending. No
original image was modified and no active model manifest changed.

Public results: docs/results/commons-incoming-v4-reviewed8.json and
commons-incoming-v4-rebin4-launch.json. The reusable full-cache auditor is
scripts/audit_commons_incoming_cache.py; it and the executed private launch/
freeze/startup operators are archived under their output receipts.
