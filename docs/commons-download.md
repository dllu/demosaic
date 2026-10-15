# Expanding the Commons archive

The existing Quality Images archive at `/mnt/external/qi` resumed on
2026-10-15 at 23:44:50 UTC. At startup it contained 77,025 verified originals
(195.2 GiB), with 380,719 pending files (4.23 TiB). Discovery and attribution
enrichment were already complete, so this job runs only the download phase.

The detached job uses the existing `pupphoto/download_quality_images.py`,
three workers, at most 0.5 request starts/second, and a **512 GiB free-space
reserve**. The downloader accounts for in-flight files before admitting work,
resumes partial downloads, and verifies size/SHA-1 before publishing originals.
The reserve leaves room for prepared data, model checkpoints and evaluations;
the complete pending archive exceeds the SSD's current free capacity.

Operational files:

- Log: `/mnt/external/demosaic/downloads/commons-qi-resume.log`
- Startup receipt, source hash and baseline database counts:
  `/mnt/external/demosaic/downloads/commons-qi-resume-receipt.json`
- Launcher PID: `.cache/commons-qi-download.pid`
- Cooperative single-job lock: `.cache/commons-qi-download.lock`

Inspect progress without starting another job:

```bash
tail -20 /mnt/external/demosaic/downloads/commons-qi-resume.log
source scripts/env.sh
uv run --no-sync python ../pupphoto/download_quality_images.py status \
  --root /mnt/external/qi
```

After a clean stop, resume with `bash scripts/resume_commons_qi.sh`; use `nohup`
and redirect output to keep it independent of a terminal. `QI_RESERVE_GIB`,
`QI_WORKERS`, `QI_REQUESTS_PER_SECOND`, `QI_DOWNLOADER`, `QI_ROOT` and
`QI_LOG_FILE` override the defaults. The script refuses to start while another
copy holds its lock. To stop gracefully, send SIGTERM to the downloader Python
process; it records completed work and finishes active writes.

Downloading does **not** change an active training or evaluation manifest.
V28/V29 and the next matched representation trial keep the frozen 44,732-source
audit. A later dataset version must prepare the new licensed originals with
linear-light 8×8 binning, screen duplicates against the existing protected
splits, and record a new manifest before training. Existing validation/test
membership and the excluded GFX scene/siblings remain fixed.
