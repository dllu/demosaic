# Local phase fitting strengthens the crossing mesh

Recorded: 2026-11-02T15:03:57-08:00 (America/Los_Angeles).

Previous goal turn: progress. Commit35b66b2 added actual complete102MP scalar
correction, RGB16 exports and the wider sky check. This turn investigates the
remaining crossing-family loss. The goal remains active; neither this increment
nor the previous one completes weak-detail recovery or general flat safety.

Both fundamental families were already selected and passed the global gate in
the centred fence patches. A higher-band diagnostic found little evidence in
most windows; it did not justify forcing new harmonics. Instead, the scalar
envelope cannot repair phase variation caused by perspective/curvature or an
imperfect frequency bin. The new local complex envelope fits sine/cosine jointly
to both physically offset measured greens, then rotates/scales all three global
RGB phasors together. Fixed sigma32, local power shrink9, magnitude cap3,
global gate9 and32-pixel aprons were chosen before fresh validation. The selector
and old global/scalar helpers are unchanged; covariance is a fixed-fit noise
proxy, not calibrated confidence. GT/reference never enters correction.

The exploratory centred crops showed clearer crossing lattice under both priors.
Reused16-recipe support showed lower active-recipe full error and about43% less
added blank structure; that reused support is development, not blind validation.
The policy was then locked before generating64 fresh recipes, seeds2026110230–
2026110293. The generator preserves the same hard dark regime: native256 via
continuous512→geometry→area2, scenelevel0.02, nominal ISO6400 shot0.00128/read
variance6.5536e-6, ADC16/black0.03. Present/absent x4 CFAs gives512 fresh
observations. All512 actual V143 root/DINO calls complete with full model,
backbone, input and RNG checks. There are zero new V120 control calls, training
updates or RAW decodes. The neural snapshot has70 modules; the new full
postprocessor has71, preserving earlier70/69-module source and receipt bytes.

Only recipes2026110260/2026110273 activate, four CFAs each. All256 absent
observations and the other62 present recipes retain every parent value.
Across all256 present cases, parent/scalar/complex mean spatial RMS is
10.390565/10.250682/10.259110 DN16 and full256 RMS9.168735/9.081861/9.087408.
Scalar has slightly better texture recovery. Mean added blank-region RMS falls
.0262366→.0209540 DN16 (−20.13%); worst per-case value2.611956→1.538151
(−41.11%). Blank error6.450122→6.448227 still exceeds parent6.446367.
This is nonuniform: recipe260's mean added blank field increases.267436→.572921,
blank error7.192332→7.229125; recipe273 improves1.411704→.768133 and
6.723955→6.565919. Both active recipes have slightly higher texture error than
scalar. The report shows both active examples and the first inactive recipe,
selected after full evaluation; all64 recipes remain scored and disclosed.

The independent audit checks all1536 rows with a joint10-column affine/template
solve (max gain difference7.4082e-15), direct spatial/DC/full/error/blank/delta
reductions, and public pixel parity on1024 fresh/reused patches:201,326,592
values exactly match the locked private prototype. Twelve full-context scalar
compatibility checks agree within float32 rounding. All96 photographic and48
analytic uniform inputs per V120/V143 parent retain their pixel values. The
previous924-window large-flat test had zero selected peaks; unchanged selection
therefore gives a logical exact bypass, not a newly executed independent test.
Dense physical WLS/covariance and bending-phase tests plus prior inference/export
checks pass54 tests, with one additional actual CLI/export test using an explicitly
declared neural stub:55 total. No stub execution enters scientific forward counts.

The frozen public implementation refines the same three actual complete101.996MP
V143 parents and normalized RAW arrays from the prior scalar study, with no
additional neural calls, RAW decodes or noise draws. Native comparisons show
more crossing mesh, especially right; recovery stays soft/uneven and regular
window placement weakens some centred-patch gains. Main foliage stays painterly;
building/larger-fence changes are small. Both priors, both camera JPEGs and all
four main standing ROIs are preserved. Independent ISO100/AHD/JPEG references
remain explicitly not exact GT.

Every parent channel remains unchanged in the same previously input-selected
2.88MP sky box[5200,200,2400,1200]. Strongest added fields are bright signs:
at the selected160px regions complex/scalar RMS is1098.29/678.41 DN16 main,
1843.62/920.06 nominal mesh and1584.88/799.16 nearby mesh. Max complex single
change reaches9037.89 DN16. Shared−2EV native views reveal highlights instead
of clipping them. Stronger edge/color changes do not prove correct lettering;
this is a remaining limitation, not an omitted positive-only selection.

CPU correction takes134.18/103.55/126.64s main/nominal/nearby in three concurrent
jobs, one BLAS/Torch thread each. These are contended observations, not a speed
ranking against prior sequential runs. All917,962,668 linear RGB16 channels
verify exactly against saved FP32 clip/round/orientation. Full sRGB16 previews
agree with independent float64 rendering within one output DN16;16-bit/ICC tags
verify. Independent rendering/native-copy checks cover8,678,400 PNG channels
across24 actually viewed boards, including three fresh exact-procedural-GT
triplets. All crop pixels remain native160 and never resize.

`infer --phase-harmonic` now defaults to the complex envelope for the targeted
real-mesh benefit. `--phase-harmonic-envelope scalar` preserves the useful
amplitude-only alternative and prior results. General inference keeps the stage
disabled. Learned weights are unchanged; V120 remains the validated general
recommendation. README shows the new full-frame fine-mesh/JPEG rows and retains
the V143 photographic faint triplets. Current docs describe useful gains,
nonuniform costs and explicit legacy reproduction; old machine receipts are copied
byte-for-byte rather than rewritten.

Evidence root: `.cache/quality-20261102/harmonic-frequency-refinement-v1/`.
Public implementation: `src/demosaic/phase_envelope.py`; report:
`docs/complex-phase-envelope.md`;24 native PNGs and full panel provenance:
`docs/images/complex-phase-envelope-v1/manifest.json`. Locked policy, original
snapshot binding,512-call collection, all fresh/reused metrics, independent
audits, full-frame executions and export/publication receipts are under
`docs/results/complex-phase-envelope-*-v1.json`. No unavailable source DAS
access or original-file modification occurred.

Next issues remain substantive: missing very weak recipes, residual/nonuniform
partial-texture spill, stronger highlight changes, window dependence, V143 broad
full427/camera quality and speed. Local agreement between separately measured
green phasors is a possible next confidence check; it has not been implemented
or evaluated here. The goal is not complete.
