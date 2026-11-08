# Flat spatial-loss completed quality and tradeoffs

Recorded: 2026-11-08T02:41:33-08:00 (America/Los_Angeles).

V181's single matched continuation, raw/EMA review, independent audits and actual
native viewing are complete. Original train PID852882/create1794132873.37,
review PID857081/create1794133893.38 and completion controller
PID854999/create1794133470.67 are terminal. No successful prefix, review,
training audit, quality audit, reduction or rendering was replayed.

The added clean-flat spatial loss produces a useful quieter local recipe, with
weaker detail. Versus V180, quiet spatial RMS falls1.106%/0.431% raw and
1.152%/0.474% EMA for ISO6400/12800; all32 inputs improve at each endpoint.
Quiet total falls0.900%/0.306% raw and0.960%/0.348% EMA, improving31/32 raw
and32/32 EMA. Mesh response falls8.372% raw/8.750% EMA to4.14334%/4.15043%
of exact constructed GT amplitude;235/256 raw and234/256 EMA responses fall.
Natural fine-band response falls on all128 inputs at both endpoints. Present
blank RMS improves while blank DC error rises, consistent with the added term
excluding per-channel means. Standalone512 spatial RMS falls about0.18–0.19%,
but coarse32 results remain mixed and broad mottle persists.

EMA still has5.783% more mean mesh response than global V178 and7.048% more
than V172, with only90/256 inputs increasing against either. Versus V172,
quiet total changes−0.214%/+0.109%,spatial−0.058%/+0.283%. This is a useful
local quiet/detail option, not a combined solution or a new universal winner.
Keep the local architecture as the detail-development baseline, V181's quieter
recipe beside V180's stronger response, V172 balanced, V173 quiet, V171 flats,
V175 raw quiet and V161 stronger learned response. V120 Small stays the broad
photo/camera recommendation. README and current documentation now state these
strengths and remaining weaknesses directly.

Actually inspected all60 native figures/12 triplets in15 original-detail sheets.
Mesh2302 is nearly uniform at normal contrast; contrast40 shows less periodic
modulation than V180 under the broad colored field. Mesh2309 still lacks the
weak crossing. Both fine cab windows/profiles remain soft/incomplete, without
clearly recovered new crossings. Main sky looks smooth at exposure4; building,
foliage and natural bird/butterfly/bark remain soft. Amplified quiet steps/bars/
stripes and gray/color flats have slightly less fine structure but persistent
broad green/purple mottle. ADC bark/fur and four planes preserve frozen output.

The original737-source worker and98 neural files remain exact. One continuation
adds900 updates/3,600 images over1,000 cached rows with100ADC skips, starting
from the same genuine V172 raw/Adam/EMA initializer and zero local adapter.
Genuine row8 restoration resumes at row9 with zero replay. Independent audit
passes every row, all900 eight-term FP32 totals and all five strict raw/EMA/
Adam/frozen/RNG checkpoints. Network clocks finish1800,adapter900. Peak CUDA
allocation 6,774,930,944 bytes. The two completed admission probes are separate;
their checkpoints never initialize this trial.

Review completes1,644 wrapper/frozen calls,1,500 network/projection,7,500sampler,
1,644 exact frozen replays and144ADC identities. Independent quality audit
checks6,576 input bindings,72RGB+72residual arrays,53,772,288 addition channels,
582native scalars,278Decimal means and750 exact input-only raw/EMA evidence
pairs. This does not independently recompute spectra or calibrate confidence.
Actual reduction keeps17methods/13,974rows/28contrasts/1,050cells,including
both V175,all four V178,both V180 and both V181 endpoints;2,313Decimal means
and11,226paired checks pass. Reused development data and warn-only atomic
sampler backward establish neither blind validation nor seed uncertainty.

Two strict CPU exports bind training checkpoint SHA256
681fe36fc73a9b4a75cb682980a653ad3412ff0df295b8307caee9ce299b6a96.
Raw export b1412b4ce90a249750c275561967de92bcc4b44e42251acc7edce5c2766f5ad6;
EMA export62a293c27b9f0443904ac76428578df0033b0c64336927e6188e62763ec51486.
The actual viewer defaults V180 EMA/V181 EMA and retains eight distinct method
states. All480 browser crops/36,864,000RGB channels match source PNGs exactly;
raw/EMA metadata,click/F flipping,navigation and absence of JS errors pass.
Marked preparation fixtures and rejection evidence remain separate and preserved.

The report includes both protected GFX families, both fine cab ROIs/profiles and
JPEGs, main sky/building/foliage/coarse fence, and12 unresized noisy/restored/
exact constructed-GT triplets. README retains two new quiet triplets and links
both mesh triplets. Identical coordinates, physical noise, exposure, contrast,
anchor and per-method checkpoint metadata remain bound. ISO100/AHD/JPEG views
are independent qualitative references, not exact GT or scoring targets;
aperture/exposure/processing/moving subjects differ. Protected captures,JPEGs
and siblings remain excluded from training. Only cached inputs/parents are
used; no new sensor/source draw,parent/DINO,RAW decode or originals/dataz access.
All new artifacts use the external SSD and repository within reserved space.
The joint fine-detail/quiet-field goal remains active.

[Completed comparison](../docs/flat-spatial-evidence-comparison.md) ·
[Native viewer](../docs/images/v181-flat-spatial-evidence-v1/native-viewer.html) ·
[Exact execution/evidence/export index](../docs/results/v181-flat-spatial-evidence-final-v1.json) ·
[Actual browser proof](../docs/results/v181-flat-spatial-native-viewer-verification-v1.json) ·
[Final independent publication verification](../docs/results/v181-flat-spatial-evidence-publication-verification-v1.json).

