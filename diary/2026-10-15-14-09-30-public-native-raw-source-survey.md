# Additional public native RAW candidates

While V24/V25 train, fetched raw.pixls.us's repository catalog and archived its
hash. Of 2016 rows, 1870 individually link CC0, covering 925 make/model pairs.
Fetched metadata only for nine distinct cameras: Nikon Z7/Z7II, GFX50R/GFX100S,
Leica Q2/SL2, Sony a7RIV/a7RV and Panasonic S1R. All selected metadata show
ISO 50–100. No RAW pixels downloaded or used; V24/V25 datasets are unchanged.

The initial scout assumed every candidate had an EXIF link; corrected it to
skip missing links and tolerate single/double-quoted HTML. Catalog and metadata
hashes and individual license links are recorded. No HTML is executed.

This is a potential source of camera-native low-noise targets, pending actual
Bayer geometry, bit depth, source checksum and protected-source/scene duplicate
checks. The GFX50R metadata filename matches the user's naming convention,
so public/user overlap is plausible and must not be ignored. No dataset
independence or quality improvement is claimed.

External authoritative receipt:
`/mnt/external/demosaic/references/raw-pixls/scouting.json`.
Repository summary: `docs/results/public-raw-candidate-survey.json`.
