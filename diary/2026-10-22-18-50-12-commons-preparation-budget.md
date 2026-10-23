# Budget bounded Commons preparation against current quality-study headroom

Recorded: 2026-10-22T18:50:12-07:00 (America/Los_Angeles).

Prepared the existing bounded-download ingestion tools for an explicit SSD
budget. Their old hardcoded560GiB preparation and500GiB reviewed-freeze floors
would block a new24.47GiB estimated cache payload with roughly338GiB free,
despite capacity for the bounded batch and ongoing quality work. Both historical
defaults remain; an explicit integer reserve must be at least256GiB.

The producer still requires the entire two-scale payload plus4GiB margin above
the chosen reserve before freezing and starting, then checks resources through
preparation/audits. A prospective288GiB reserve adds32GiB for remaining training
checkpoint/evaluation/full-frame writes above the active256GiB quality floor.
Recalculate from the actual final arrivals and available storage before launch;
do not treat this estimate as a completed preparation or data admission.

All37 focused downloaded-preparation/review-freeze tests pass, including invalid
reserve rejection before output/input operations, an exact additional-byte
boundary, one-byte-short failure and the independent48GiB memory guard. Ruff
and formatting checks pass. Source selection, numerical cache operators,
protected screening, duplicate/neighbor/manual review and old manifests stay
unchanged. The producer takes the downloader's singleton lock, so it must wait
for the original controller/child to exit. Their336GiB reserve and current
training/evaluation/full-frame plans were not changed or restarted.

[Source hashes, tests and declared budget](../docs/results/commons-bounded-preparation-budget-v1.json).
