#!/usr/bin/env bash
# Resume the existing archive without changing frozen training/evaluation manifests.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
source scripts/env.sh

downloader="${QI_DOWNLOADER:-$repo_root/../pupphoto/download_quality_images.py}"
archive_root="${QI_ROOT:-/mnt/external/qi}"
log_file="${QI_LOG_FILE:-/mnt/external/demosaic/downloads/commons-qi-resume.log}"
mkdir -p -- "$(dirname -- "$log_file")"

# The downloader already checks size/SHA-1, resumes partial files, and accounts
# for in-flight downloads before enforcing its free-space reserve.
exec flock --nonblock .cache/commons-qi-download.lock \
    uv run --no-sync python "$downloader" download \
    --root "$archive_root" \
    --workers "${QI_WORKERS:-3}" \
    --requests-per-second "${QI_REQUESTS_PER_SECOND:-0.5}" \
    --reserve-gib "${QI_RESERVE_GIB:-512}" \
    --log-file "$log_file"
