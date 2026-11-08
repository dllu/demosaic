V180's local measured-phase fields produce a useful mesh-response gain at a
higher quiet-field cost. Raw/EMA reach **4.52194% / 4.54843% of exact constructed
GT amplitude**, versus global V178's 3.92428% / 3.92355%. That is **+15.230% /
+15.926% relative response** at the same 3,120-adapter-weight budget and cached
900-update recipe. Gains are uneven: 122/256 raw and 142/256 EMA inputs increase;
the others decrease. Relative to the unchanged matching control, gains are
16.290% / 16.987%. Against V172 EMA, local EMA gains **17.313%**, with 184/256
inputs increasing. The mean still retains less than one twentieth of exact
constructed amplitude. This is a useful detail architecture to build on, with
V172 and the earlier quiet/flat/detail options retained for their strengths.
V120 Small remains the broad photo/camera recommendation.

The cost is clear. Against same-endpoint global V178, local EMA quiet spatial
RMS rises **1.054% / 0.786%** for ISO6400/12800; 16/16 and 15/16 inputs worsen.
Quiet total RMS rises **0.844% / 0.511%**, with 16/16 and 14/16 worsening.
DC RMS changes +0.272% / −0.279%. Raw has the same tradeoff: quiet spatial
+1.016% / +0.758%, total +0.816% / +0.500%. Mesh-present blank RMS rises
0.098% raw / 0.104% EMA, and absent full RMS rises 0.038% / 0.042%. Near-zero
signed absent-template gain does not rule out mottling or false fine texture.

Standalone512 EMA full-flat RMS changes −0.030% / +0.001% versus global V178,
while spatial RMS rises 0.021% / 0.042% and coarse32 RMS changes +0.007% /
−0.010%. Relative to V172 EMA, local EMA full-flat RMS rises 0.086% / 0.016%,
quiet total RMS rises 0.753% / 0.458%, and quiet spatial RMS rises 1.106% /
0.760%. Thus the higher mesh response does not combine the earlier quiet/flat
strengths. V161 still has stronger learned response, about 5.24% of GT, with
larger quiet errors. V173 retains its stronger quiet-spatial gain, V171 its
standalone-flat gain, V175 raw its small quiet-total gain, and global V178 its
smaller mesh-response gain at a smaller quiet cost.

Natural photo response changes are small. Local EMA band response rises
0.252%, 0.084%, 0.136% and 0.008% across retained faint/dark and organic faint/dark
means versus global EMA. Relative band error changes +0.0054%, +0.0077%,
−0.0009%, +0.0073%. Stronger band response alone is not better fine-band fidelity.
There is no broad photographic quality or safety claim.

All **60 actual native figures in 15 original-detail sheets** were inspected,
including 12 unresized noisy/restored/exact constructed-GT triplets. Mesh2302
still looks nearly uniform at ordinary display. At contrast40 the local outputs
show stronger fine periodic modulation under broad colored error, without a
clearly recovered complete lattice. Mesh2309 retains mostly one orientation
and still misses the weaker crossing. Both fine green cab ROIs remain soft and
incomplete under both supplied noise profiles; changes are subtle and do not
clearly recover the independent reference's crossings. Coarse fence strands
survive, while building/foliage and natural bird/butterfly/bark detail remain soft.

The main sky looks smooth at ordinary exposure4. Noisy gray/color flats retain
broad green/purple mottle at contrast40. Quiet regions beside steps, narrow bars
and stripe patches acquire somewhat stronger fine mottled/striped error on top
of the broad field, consistent with their higher spatial RMS. At ordinary
contrast these fields look nearly smooth. ADC bark/fur and four ADC planes keep
the exact frozen output. These controls do not establish noisy-sky safety.

The report includes both protected scenes: DSCF3879 ISO6400 / independent
DSCF3880 ISO100 f/5.6 for sky/building/foliage/coarse fence, and DSCF3842 ISO6400 /
independent DSCF3835 ISO100 f/5.6 plus both straight-out-of-camera JPEGs for the
fine green mesh. **ISO100/AHD and JPEGs are qualitative references, not exact GT**;
aperture, exposure time, processing and moving subjects differ. No real-reference
pixelwise scores are used. Captures, JPEGs and siblings remain outside training.
Cached arrays and cached parent predictions are used; originals and unavailable
`/mnt/dataz` remain untouched.

The mesh triplets retain native ROI `[176,176,160,160]` in 512px RGGB contexts,
display exposure8/contrast1, shot .00128/read variance 6.5536e−6. Fine cab crops
retain the cached `[600,6260,768,768]` context and native ROIs
`[206,229,160,160]` / `[426,189,160,160]`, display exposure16. Other views keep
their exact prior source, noise, ROI, exposure, contrast and anchor in the
manifest. Training checkpoint SHA256 is
`9c749aa681260bb79ec11b077c596c7dc68bb35c099ddcf44670d8bcfe8e6af8`.
Both endpoint exports record class/config/source, source checkpoint, raw/EMA
state and module hash; four existing V178 viewer states retain separate metadata.

One actual continuation adds 900 updates/3,600 noisy images across the same
1,000 cached rows with 100 ADC skips, starting from V172's real raw/Adam/EMA
history. Existing 141 network clocks finish at 1,800; the adapter finishes at
900. The exact frozen V178 training engine is configured explicitly with the
local factory and paths. Genuine row8 restoration resumes at row9. Independent
training audit passes the full trace, 900 FP32 loss totals and all five raw/EMA/
Adam/frozen/RNG checkpoints. Peak allocation is about 6.28 GiB. The two earlier
fresh-Adam admission probes are separate from this initializer.

All 822 fixed cases are reviewed at both endpoints: 1,644 wrapper/frozen calls,
1,500 matching/projection calls and 7,500 samplers. All 1,644 exact frozen replays
and 144 ADC identities pass. The independent quality audit checks 6,576 input
fingerprints, 72 RGB plus 72 residual arrays, 53,772,288 addition channels,
582 native metric scalars, 278 Decimal means and 750 exact input-only raw/EMA
local metadata pairs. It checks geometry and finite local powers without
independent spectral recomputation or confidence calibration. No parent/DINO,
new sensor/source draw or RAW decode occurs during this continuation/review.

All 15 comparison methods, both V175 endpoints, four V178 endpoints, 12,330
rows, 22 contrasts and 882 table cells remain available. Completed V178 outputs
are reused, not rerun or bit-exact paired retraining; sampler atomic backward
retains the existing warn-only nondeterminism. Local windowed nuisance fits,
aggregation and interpolation change together, so equal parameter counts do
not isolate a single mathematical cause. Defaults followed a training-only
support diagnostic. This reused development stream has no blind or seed-uncertainty
estimate. [Execution, preparation and actual viewing provenance](results/v180-local-phase-completion-execution-v1.json).
