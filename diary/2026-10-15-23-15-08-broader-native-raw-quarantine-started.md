# Broader native RAW selection and reusable quarantine producer

The previous goal turn made progress: a50ea37/b5be422 implement and verify an
explicit inference precision policy, preserving learned tensors and near-
identical quality while reducing observed full-frame mean time. Current state
revalidates those pushed commits and terminal evaluation/benchmark handles.
The next major effort returns to the unmet quality objective, starting with
more native scene diversity than the current31/37 scenes.

A frozen raw.pixls.us CC0 metadata survey inspects291 entries across185 models
and selects138 low-ISO camera models across nine makes. Candidate ISO50–200,
catalog≥20MP, ordinary/full-area modes; actual decode/content/scene uniqueness
still require verification. Survey SHA
`c3f4e85966f7164fb77e530c8e5563c2e5742866ebde001144a7077cae46d9fd`.
Oversized metadata responses are explicitly excluded; a metadata-URL space
encoding issue was corrected, and verified local metadata was reused.

Existing `fetch_public_raw.py` now acquires this frozen selection under its
own lock, two workers and512GiB reserve. Live downloader PythonPID863218,
uv parent863215, unified-exec session55493. At23:15 inspection109 files/4.50GB
were present; this includes active temporary files and is not a count of all
verified sources. Training datasets remain frozen. The Commons downloader
PID3989567 remains live independently; no duplicate downloader was started.

Added `scripts/prepare_public_raw_quarantine.py`, a reusable locked/resumable
producer using the existing native binning. It checks actual bytes, Bayer, ISO,
size, protected exact hashes, held-out camera aliases and the entire standing
GFX date/file family. Per-capture atomic outcomes preserve completed work;
changed recipe/cached bytes fail. It retains4×/8× camera-linear uint16 targets,
raw metadata, near-white stats and inspection-only renders. It never admits
sources to training; source clipping/content/overlap review and a SHA-pinned
admission remain required.

Actual GFX50R file2979 smoke: bin4/bin8/screen SHA matches the original producer
exactly. Verified restart reuses target bytes without changing their mtimes.
All342 tests pass in26.95s; targeted20 acquisition/protected-identity checks pass
in1.83s. The producer's metadata/date tests reject siblings such asDSCF3895 on
the standing GFX date, not only the four named files. No model performance or
protected-final scoring occurred. See docs/public-raw-expansion-v2.md.
