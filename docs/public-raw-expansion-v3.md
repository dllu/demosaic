# Additional public camera-native candidates

A new bounded metadata survey identifies **36 new CC0 low-ISO RAW candidates**
across Canon, Nikon, Olympus, OM System, Pentax, Samsung and Sony. No new RAW
payload has been acquired, decoded or admitted at this observation. These are
candidate files, not verified independent scenes or a trained quality gain.
[Frozen metadata, prior-source filtering and tests](results/public-raw-expansion-v3-metadata-v1.json).

The survey reuses the immutable2,016-entry catalog snapshot from the earlier
public work; it does not claim to cover the latest catalog. It checks62 models
absent from the prior-v2 metadata records, with at most two variants/model and
eight models/make, requiring explicit per-entry CC0 links,≥12 catalog MPix and
metadata ISO≤200. Monochrome, reduced/pixel-shift/crop modes and declared unseen
camera aliases are excluded. Actual Bayer geometry and dimensions still need
decoding checks. At most one metadata request starts per second, with20s
timeouts and a1MiB response cap. Oversized/unsuitable responses remain excluded.

Seventy-nine metadata requests yield37 low-ISO matches. A second identity filter
checks every previously acquired pilot/v2 file and current native source hash;
it removes one already-acquired Panasonic file, leaving36. This separates the
earlier pilot from the prior-v2 model list and avoids a redundant RAW download.

The current public native manifest contains128 captures across78 camera models;
most contribute one source. The user's local RAW directory contains RAF files
only, so this survey uses public sources without accessing the archive drives.
The user's other qualitative camera captures and standing GFX family remain
protected. The [publisher](https://raw.pixls.us/) requests low-ISO scenery and
provides per-entry license links; selection requires each actual CC0 link,
published RAW SHA256 and pinned EXIF payload, not a site-wide assumption.

Acquisition now accepts CR2/CR3, PEF, ORF, SRW and NRW containers in addition to
the existing formats. Accepting a container does not establish its decoding,
CFA, exposure, quality or admission. All existing host, license, catalog/metadata,
publisher-checksum and standing-capture checks remain. Nine new suffix tests
cover accepted containers and rejected JPG/ZIP/EXE names; together with existing
acquisition/quarantine tests,29 pass. Ruff passes. No neural/training-core file
changes and no active recipe changes accompany this work.

Next acquire only the frozen36-source selection into a new quarantine root,
then use the established phase-aligned4×/8× producer. Full source hashes,
ordinary Bayer/ISO checks, source clipping, actual content review, grouping and
protected/Commons/native/intra-candidate comparisons precede any new pinned
admission. Camera-native targets remain low-noise estimates, not exact noiseless
GT. The current original20k V84/V85 study retains its fixed inputs.
