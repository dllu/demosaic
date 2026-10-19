# Stage more Commons originals locally while training continues

Previous goal turn was a verified wait plus the actual connected2k checkpoint
finite-state check. Revalidated current training and queued review/CPU closure
owners; connected training advances beyond2k with the original4k budget. Main
PROMPT quality, broad real superiority and100MP10s remain unproven.

Revisited the standing request to download additional QI images. External free
space is about502.1GiB, below its512GiB downloader reserve and near the current
model worker500GiB launch guard. Local free space is about254GiB. Prepared a
separate local-only16GiB original-content subset, with224GiB local reserve,
2download workers/.25 request starts per second. Neither active training
manifests nor the external archive/index are modified.

Added scripts/stage_commons_local.py. Reads source SQLite read-only with memory
temporary storage, applies the existing canonical free_license policy and
photographic eligibility/min2048px/max120MP/max256MiB-file bounds, excludes every
already-downloaded SHA1, deduplicates new SHA1s and uses deterministic page-ID
hash ordering under byte/image caps. Clone only selected records and their full
attribution, license URL, credits/HTML/extmetadata into a separate SQLite schema;
reset only download bookkeeping. Snapshot1188 selected originals totaling
17175771412bytes (<16GiB). Source index hashes remain exact before/after staging.

Copies the existing downloader/config code byte-for-byte into the local stage;
passes the existing config path without copying credentials. Its existing
HTTP pacing, partial resume, size/SHA1 publication and in-flight free-space
reserve remain intact. An inherited advisory lock survives exec and prevents
our normal archive-resume wrapper from overlapping. Source root/selection/
immutable metadata checks precede network setup. Tests cover invalid limits,
low disk, moved roots and changed license/hash/attribution:8 pass in1.16s.

The actual detached downloader PID3014422/creation1792388876.49 is live and has
published new verified files. Independently rehashed12 completed originals and
checked exact sizes against Commons SHA1 records; lock contention probe confirms
the shared lock is held. All1188 full attribution records match source metadata,
all new hashes are absent from172372 downloaded source entries, and actual
training frozen source/input hashes remain exact. CUDA is hidden for downloading.

Published docs/commons-local-staging.md and startup JSON evidence, with a small
link from commons-download.md. New originals stay quarantined: full integrity,
duplicate/protected-scene/content/split screening and separate future data study
remain required. No semantic-diversity claim, preparation, automatic admission,
GFX-family use, source-HDD reads, model/default/README/PROMPT change, current
budget extension or GPU inference overlap. Main corpus reconciliation later must
account for the local index to avoid downloading these originals twice.
