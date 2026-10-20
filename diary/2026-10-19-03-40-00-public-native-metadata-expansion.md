# Broader RAW-container support and36 new low-ISO metadata candidates

Verified the original20k control trainer, archive downloader and review waiters
live. The local photo root contains RAFs only; no archive drives were read.
The existing public native manifest has128 captures/78 camera models. The earlier
commentary's79 was an off-by-one; the manifest count is78.

The new metadata-only scout checks62 models,79 bounded requests, and finds37
explicit-CC0 ISO≤200 candidates. Prior-v2 model filtering alone misses earlier
pilot identities, so an additional all-prior-acquisition/current-source SHA/ID
filter removes Panasonic3652, leaving36 across7 makes. It uses the existing
frozen2016-row catalog and does not claim latest/complete coverage. Oversized
metadata and unsuitable ISO remain excluded under its fixed1MiB/20s policy.

Added CR2/CR3/PEF/ORF/SRW/NRW acquisition suffixes while retaining every existing
CC0/catalog/metadata/host/publisher-checksum guard. Nine new suffix tests plus
20 existing acquisition/quarantine cases pass (29 total), with Ruff. No model
or training-core bytes change. Payload acquisition, actual raw decoding,
source clipping/content/overlap/grouping and admission remain pending. The
standing GFX and personal qualitative frames remain protected; no new model
score or training input changes.
