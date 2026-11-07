# V169 preserves response while reducing quiet color bias

Recorded: 2026-11-07T13:23:00-08:00 (America/Los_Angeles).

V169 is complete as a fixed-weight inference intervention, with no retraining.
Removing a sigma8/radius24 native Gaussian lowpass from V168's direct RGB
correction lowers quiet RMS3.74–10.69% and DC color bias11.45–31.59%. Mesh response
stays essentially unchanged at3.806–3.837% of constructed GT. All48 coarse-flat
errors worsen; full-flat means rise .389–.705%, quiet spatial error .167–.267%.
All32 raw and31/32 EMA quiet spatial inputs worsen; quiet total improves26/32
raw and24/32 EMA. This retains the V168 response gain with lower added DC bias,
while preserving important spatial/flat costs. [Final report](../docs/balanced-spatial-correction.md).

Branch ablations show direct RGB provides much of the useful standalone coarse
correction and much of the quiet color bias at these fixed weights. Spectral-only
response is3.730/3.765% GT,direct-only2.277/2.273%,parent2.202%. The balanced path
retains more response and lower flat error than spectral-only. This is functional
evidence, not a claim about the cause of training behavior or blind generalization.
All72 ADC cases per endpoint retain V168 output fingerprints exactly.

Actually viewed72 native figures/24triplets in18 original-detail sheets. Quiet
and dark-flat contrast40 crops retain large colored patches despite changed
overall balance. Fine cab left remains largely erased;right keeps one wire
direction more strongly than crossings under both priors. Ordinary sky stays
smooth at exposure4; building, foliage and coarse fence remain similar. Natural
microtexture stays smoothed,ADC detail unchanged. ISO100/AHD/JPEG views are
qualitative references,not exact GT. README now includes two native balanced
mesh and two balanced quiet triplets beside V161 stronger detail and V165 grain.
Older views/receipts remain intact.

The actual review worker4132908 completed1644 GPU root forwards and exact original
V168 replays,with6576 streamed method rows. No source/noise,parent/DINO or training
calls. Full new arrays are retained only for36 preselected native cases:216 new
predictions plus72 direct corrections (.801GiB). An independent posthoc audit
checks all replay/input/journal bindings,19760 scalar comparisons,288 saved
original/new predictions and72 corrections. It reconstructs53,772,288 selected
balanced-output channels. In-process independent filter checks cover1,186,725,888
correction channels,maximum filter difference2.13e-10 normalized. Independent
Decimal means check1105 reductions,maxdifference7.11e-15. Rendering checks
23,961,600 new channels and copies26,803,200 old channels exactly. No complete
new prediction archive or broader posthoc full-array audit is claimed.

Both actual transferred endpoint states load strictly with47 tensors/124909
parameters;all90 old neural sources unchanged.47 relevant CPU tests,including19
new independent filter/carrier/embedding/gradient tests,pass. Six CPU/CUDA filter
value/gradient cases and three autocast checks pass. Formatting and closure
binding cleanup in current helpers preserves saved metric/render behavior;
[current-source parity](../docs/results/v169-current-source-parity-v1.json)
records rerun CPU checks and exact native PNG equality. Actual frozen execution
sources remain unchanged in the published evidence.

The preparation assertion and missing-SciPy import occurred before any neural
forward;both originals remain preserved. The final worker uses the independent
NumPy oracle. At954 returned forwards,local headroom paused the same live owner.
70 owned derived mesh fixtures moved byte-exact to fast SSD,with original-path
links,freeing .752GiB. It resumed without repeating completed work;56/116GiB
guards remain unchanged. Originals did not move and dataz was not read. The
two recorded review owners are terminal. A pre-execution reduction-label correction
uses decreased/increased counts instead of implying that smaller signed response
is always better. No scientific result was rerun by that bookkeeping change.

Balanced raw export SHA256:
`9088b290ce3518b8e99326ce5dc9e88f507c47210419f93ad4a9e6fbe8316879`.
Balanced EMA export:
`2184e9fc4c462eb8d740baa32b8e4fd569a18d80cca6f00a710ff9af51408562`.
[Final evidence](../docs/results/v169-balanced-spatial-final-v1.json) ·
[Publication verification](../docs/results/v169-balanced-spatial-publication-verification-v1.json).

The goal remains open: accurate fine low-contrast crossings and reliable flat
regions are not achieved. This result supports pursuing coarse corrections that
respond differently in standalone flats and quiet neighbors,while retaining
V168 fine-family coverage. V168 coarse,V165 total-flat/grain,V161/V164 detail,
V166 quiet color,V158 quiet accuracy and V157 coarse capacity stay available.
