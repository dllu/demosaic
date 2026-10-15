# Resume Commons Quality Images in the background

The user requested more scene diversity and authorized resuming the partial
download while model work continues. Inspected the existing downloader and
confirmed no other downloader was running. Discovery and attribution metadata
were complete. Baseline: 77,025 downloaded, 380,719 pending, two failed, 2,477
excluded; SSD 46% used, approximately 2,013 GiB free.

Started a detached download-only job at 23:44:50 UTC using the existing SQLite
state and originals directory, three workers, 0.5 request starts/s and a 512 GiB
free-space reserve. The script already reserves in-flight bytes, verifies SHA-1
and size, and resumes partial files. No original is intentionally rewritten.
The tracked `scripts/resume_commons_qi.sh` adds a cooperative lock and keeps
caches/logs within authorized storage. No changes were made in the pupphoto
repository. Startup receipt/logs are under
`/mnt/external/demosaic/downloads/`; see `docs/commons-download.md`.

Current experiments retain their immutable audited manifests. Newly downloaded
images need a separate preparation/deduplication review before training; no
held-out sources or standing GFX photos enter training. The current stabilized
RGB/physical-anchor software checks completed: 238 passed in 19.18 seconds.
Model quality and full-resolution speed requirements remain open.
