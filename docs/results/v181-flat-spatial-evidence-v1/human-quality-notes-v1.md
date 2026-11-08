V181 provides a quieter local-evidence option with a measurable detail cost.
Adding clean-flat spatial-error supervision to the unchanged V180 architecture
reduces quiet spatial RMS **1.106% / 0.431% raw and 1.152% / 0.474% EMA** at
ISO6400/12800. All 32 quiet inputs improve spatially at each endpoint. Quiet
total RMS falls **0.900% / 0.306% raw and 0.960% / 0.348% EMA**; 31/32 raw and
32/32 EMA inputs improve. This recovers much of V180's quiet-field cost while
retaining more mean mesh response than global V178. It is useful progress on
the tradeoff, with V180 retained for its stronger detail response and V172 for
its balanced comparison. V120 Small remains the broad photo/camera recommendation.

The cost is substantial: mean mesh response falls **8.372% raw / 8.750% EMA
versus V180**, reaching **4.14334% / 4.15043% of exact constructed GT amplitude**.
Response decreases on 235/256 raw and 234/256 EMA inputs. Present-mesh full RMS
rises 0.337% / 0.348%, even though blank RMS falls 0.201% / 0.219%. Absent full
RMS falls 0.126% / 0.137%. Present blank spatial RMS falls 0.258% / 0.284%, but
blank DC RMS rises 0.598% / 0.689%; absent DC RMS rises 0.911% / 1.073%. The
new spatial term excludes per-channel means, and quieter spatial error does
not guarantee improved color bias. Near-zero signed absent-template gain does
not establish absence of false texture.

EMA still exceeds global V178 EMA mesh response **5.783%** and V172 EMA
**7.048%**, but only 90/256 inputs increase against each. Relative to V172,
quiet total RMS changes **−0.214% / +0.109%**, and quiet spatial RMS changes
**−0.058% / +0.283%**. Only 9/16 and 5/16 improve in quiet total RMS, and 10/16
and 3/16 improve spatially. Relative to global V178 EMA, quiet spatial RMS
changes −0.110% / +0.308%. V181 therefore does not dominate these earlier
options. V173 retains stronger quiet-spatial reduction, V171 stronger standalone
flat reduction, V175 raw its modest quiet-total gain, and V161 stronger learned
mesh response with larger quiet costs.

Standalone512 full-flat RMS falls **0.089% / 0.134% raw and 0.078% / 0.110%
EMA** versus V180. Spatial RMS falls 0.184–0.193%, with 44/48 raw and 44/48 EMA
inputs improving. Coarse32 RMS changes +0.0001% / +0.0400% raw and −0.0005% /
+0.0436% EMA. The small spatial benefit leaves the broad field error unresolved.
Versus V172 EMA, full-flat RMS changes +0.008% / −0.094%, again a mixed result.

Natural photographic fine-band response decreases at both endpoints on all
128 noisy inputs versus V180. EMA falls **0.912%, 0.717%, 1.140% and 0.734%**
across retained faint/dark and organic faint/dark means. Relative band error
changes +0.0124%, +0.0083%, +0.0347% and −0.0033%. Lower spatial error on clean
flat neighborhoods can still suppress detail through shared parameters; the
target-only mask is no guarantee against that tradeoff. No broad photo-quality
or noisy-sky safety claim follows.

All **60 actual native figures in 15 original-detail sheets** were inspected,
including 12 unresized noisy/restored/exact constructed-GT triplets. Mesh2302
remains nearly uniform at normal contrast. At contrast40, V181 has less fine
periodic modulation than V180 under the broad colored field; a complete lattice
does not emerge. Mesh2309 keeps mostly one strong orientation and loses the weak
crossing. Both fine green cab windows remain soft and incomplete under nominal
and profile3879 conditioning. The differences are subtle and do not clearly
recover new crossings from the independent reference. Main coarse fence strands
survive; building edges, foliage, bird feathers, butterfly wing texture and bark
remain soft. These views agree with a quieter but less responsive candidate.

The main sky looks smooth at ordinary exposure4. Noisy gray/color flats and quiet
regions beside steps, bars and stripe patches retain broad green/purple mottle
at contrast40. V181 reduces some fine structured/mottled error versus V180,
without removing the broad casts. Normal-contrast fields are nearly smooth and
step/bar/stripe boundaries survive. ADC bark/fur and all four ADC planes retain
the exact frozen output. ADC identities do not establish noisy-sky safety.

Both protected GFX scenes remain in the report: DSCF3879 ISO6400 / independent
DSCF3880 ISO100 f/5.6 for sky, building, foliage and coarse chain link; DSCF3842
ISO6400 / independent DSCF3835 ISO100 f/5.6 and both camera JPEGs for fine cab
mesh. **ISO100/AHD and JPEG references are qualitative, not exact GT**; aperture,
exposure time, processing and moving subjects differ. No real-reference pixelwise
scores are used. These captures, JPEGs and siblings remain excluded from training.
Only cached arrays and cached parent predictions are used; originals and
unavailable `/mnt/dataz` remain untouched.

Mesh triplets use native ROI `[176,176,160,160]` in the same 512px RGGB contexts,
exposure8/contrast1, shot .00128/read variance 6.5536e−6. Quiet triplets use
ROI `[80,176,160,160]`, exposure8/contrast40 about camera RGB
`[.001500000013,.006000000052,.002666666871]`, with shot/read variance
.00128/6.5536e−6 or .00256/2.62144e−5. Fine cab views retain cached context
`[600,6260,768,768]`, ROIs `[206,229,160,160]` / `[426,189,160,160]`, exposure16.
Every view retains the prior source/ROI/noise/display transform; crop pixels are
never resized. Training checkpoint SHA256 is
`681fe36fc73a9b4a75cb682980a653ad3412ff0df295b8307caee9ce299b6a96`.
Both strict endpoint exports bind that checkpoint, source/class/config, raw/EMA
state and module hash. Six earlier V178/V180 viewer states retain separate metadata.

The intended change versus V180 is one added loss: weight .25 times domain
weight, using actual target errors in 4DN16 units and truncated17px per-channel
spatial variance inside the existing clean-range mask. All 98 neural files,
seven original terms, target mask, data and training recipe remain unchanged.
One continuation adds 900 updates/3,600 noisy images across the same 1,000 cached
rows with 100 ADC skips, from the original V172 raw/Adam/EMA history and a zero
local-evidence adapter. Network clocks finish at1,800, adapter at900. Genuine
row8 restoration resumes at row9 without prefix replay. Independent audit
passes all900 eight-term FP32 totals, full trace and five raw/EMA/Adam/frozen/RNG
checkpoints. Peak CUDA allocation is about6.31GiB. The two admission updates are
separate probes, not trial initializers.

The fixed review completes all822 inputs at both endpoints:1,644 wrapper/frozen,
1,500 network/projection and7,500 sampler calls,1,644 exact frozen replays and
144 ADC identities. Independent quality audit verifies6,576 input fingerprints,
72 native RGB plus72 residual arrays,53,772,288 addition channels,582 native
metric scalars,278 Decimal means and750 exact input-only raw/EMA evidence pairs.
This checks local geometry and finite powers without independently recomputing
the spectrum or calibrating confidence. No new parent/DINO, sensor/source draw
or RAW decode occurs.

All17 methods/13,974 rows, both V175 endpoints, all four V178 endpoints and both
V180 endpoints remain available. Two same-endpoint primary loss contrasts and
26 contextual contrasts retain1,050 table cells,2,313 Decimal means and11,226
paired checks. Earlier completed outputs are reused; this is not bit-exact paired
retraining, and sampler atomic backward remains warn-only nondeterministic. The
reused development suite has no blind or seed-uncertainty estimate. The completed
trial establishes a useful quiet/detail option, while missing real fine crossings
and broad mottling keep the joint goal open.
