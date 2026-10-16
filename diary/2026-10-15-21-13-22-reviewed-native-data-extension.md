# Reviewed native-data extension

Prepared separate4×/8× native datasets with59 captures/37 scenes, retaining every
original53 capture/31-scene row and adding six CC0 outdoor RAWs: GFX50R, Q2,
PanasonicS1R, NikonZ7II, GFX100S and Sony a7RV. Existing quarantine manifests,
source RAWs and target caches are unchanged. No screening render is a target.
Both datasets are explicit future choices, outside active V37/V38.

The data-only audit now covers42 protected references:5 known-development,
10 unseen-development,25 official-final and2 cached standingGFX. Full/75%/50%
center/corner views and eight dihedral orientations on each side use a broad
dHash<=40 OR correlation>=.95 gate. One public Q2 ferry image flags against
smooth tabletop crops in2pilesofplates, max correlation.531. Reviewed42 reference
and9 public overviews plus the full binned ferry image: clearly different scenes.
No model or protected-final performance scoring. Arbitrary views/crops remain
a limitation; this is not complete scene recognition.

The first audit failed after40 decoded references because cached personal RAFs
have SHA/size receipts without a publisher-checksum field. Preserved v1/log,
fixed that branch, ran v2 successfully on all42. Source originals stay read-only.
Source quality excludes the chart and two clipped landscapes: Sony3478 has
20.40% of binned pixels near source white, Leica7872 has3.58%; threshold0.1%.
Sony's green channels clip over roughly52% of the top third; independent LibRaw
renders also show the sky artifact. Six retained sources have <=.00047% under
the same cache check. Selection predates model performance on new data.

Admission receipt SHA367b12e3b64817ce06ba0791c4131c2bc77a75971dac2ede03fe227b732ffce0
is pinned in raw_admission.py. New train manifests embed its exact payload;
public rows must match its source/cache/camera/scene metadata exactly. Legacy
scene guards stay in place. Split flips, forged self-signing, changing WB/cache
or relabeling a public row as a legacy scene are rejected. Builder archives
inputs/code, checks real cache headers/hashes, preserves base rows, validates
the full candidate before publication and refuses existing/duplicate extensions.
No original pixels copied. Existing source snapshot/resume hashes capture
the complete embedded admission without changing training configuration APIs.

All304 tests pass in50.74s; targeted25 pass in3.47s; Ruff passes. CLI preparation
completed both datasets under raw-clean-public-extension-v1/bin{4,8}/manifest.json.
Docs/results/native-public-extension-v1.json retains manifest hashes, full
protected-screen result and manual resolution; public-raw-admission-v1.json
retains approved/excluded provenance. No quality benefit claimed yet.
