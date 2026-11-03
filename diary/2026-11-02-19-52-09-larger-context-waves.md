# Larger RAW context and measured high harmonics test faint lattice recovery

Recorded: 2026-11-02T19:52:09-08:00 (America/Los_Angeles).

The next measured limitation was context, not another learned loss: the true
fine-mesh fundamentals and higher harmonics were clearer in actual 512-pixel RAW
windows than in local256 windows. I kept the existing connected support/refit
synthesis, preserved local frequencies/inactive gates, and added separated
proposals from .03–.22/.22–.34 cycles/pixel. Physical CFA offsets, fixed affine/
Hann detrending and bounded continuous frequency fitting remain explicit.

The first relative-import prototype failed; the early high-band prototype also
left a direct WLS fit in FP32. Corrected `prototype-v5.py` casts the complete fit
to FP64 before both dictionaries are compared. Original failed folders, scripts,
logs and receipts remain preserved. A32-recipe native512 development collection
adds256 actual V143/DINO forwards; analytic low/high-band and four-CFA checks pass.
The first locked64-recipe trial uses two predeclared contrast strengths and1,024
actual neural parents. A clarification receipt expands the numeric contrast
ranges without changing the original lock bytes.

The unguarded enlarged dictionary failed an important control. On1,024 genuinely
constant nominal-noise observations analyzed with the standing nearby Haar prior,
137 context candidates were selected. The wide version changed124 controls,
sparse changed78, and46 gained a field only in the wide version. Worst wide
added RMS was .924067DN16, maximum12.92672DN16, seed202611171069. The source and
all changed raw/parent/output arrays remain archived. Matched-prior4,096 flat
controls had passed, so that success alone was insufficient.

I added a one-way variance floor for the correction: use the robust high-band
power divided by exactly propagated unit variance, subtract the supplied-noise
proxy, and retain only a nonnegative maximum over greens. Apply the scalar to
selection/local fitting/regularization, never to the neural conditioning. Texture
can inflate this quantity; it is not calibrated read noise or uncertainty.
Observed-clipped windows keep the earlier grid-TV result; inputs smaller than512
keep exact sparse behavior, including its limitations under a wrong prior.
All137 selected development failures then retained their ideal flat parents.

A second policy lock precedes fresh64 primary-contrast recipes, seeds2026111900–
1963:512 actual V143/DINO calls, four CFAs and presence/absence. The earlier1,024
trial is now historical/development for the guard, not its independent validation.
On256 fresh present observations, template response .048479→.055448 is14.38%
higher than sparse; whole512 error8.787953→8.681861DN16 falls1.21%, central160
spatial error falls1.64%. Mean added blank RMS .008341→.009783DN16 rises17.28%,
while worst1.125434→.929405DN16 falls17.42%. Response/error improve in43 cases,
regress in four and stay unchanged in209. Only12 scene recipes activate; mean
response is still just5.54% of exact procedural GT. Blank-GT error increases in
seven and decreases in seven; all256 absent neural outputs retain every pixel.

Complete public v7 reruns also retain every pixel in all4,096 matched and all1,024
Haar-mismatch ideal-flat controls, with regenerated packed-byte hashes checked.
These are repeats of4,096 unique sensor observations and declared ideal parents,
not additional independent samples or actual neural outputs. The entire study
adds1,792 actual learned forwards and5,888 unique sensor observations, zero
training updates, V120 control calls or real RAW decodes. `/mnt/dataz` remained
unavailable and untouched; all real work uses cached inputs/parents/AHD/JPEGs.

Independent joint ten-column affine/template fits and direct pixel/blank/DC/block
calculations verify all1,536 fresh metric rows, maximum gain discrepancy9e−13.
The public port matches all201,326,592 development and402,653,184 fresh output
values exactly. Four actual parent patches covering all CFAs match CPU/CUDA to
3.47e−18 without RNG changes. The earlier100,663,296-value sparse parity proof
still covers the unchanged common synthesis factoring. Integration115 and31
additional distinct tests pass,146 unique tests; the repeated25 context checks
also cover the new positive-floor clipping fallback.

Complete guarded102MP outputs, main sky/building/foliage/fence, both fine-mesh
priors, both JPEGs, native GT triplets, tail/failure controls and strongest-field
views are recorded in the [quality report](../docs/wide-phase-context.md) and its
byte-preserving publication receipts. The new mode is explicit (`wide`); the
optional-stage `edge` default and general V120 recommendation remain. The broad
quality goal stays active: very weak texture, partial-support leakage, highlight
color, confidence calibration and100MP/10s performance remain unresolved.

Final native inspection covered all31 boards in nine original-resolution sheets.
The real crossing mesh is stronger under both priors but remains soft. The tested
2.88MP sky has zero changed channels. Crucially, the worst amplified procedural
tail retains a detached stripe island outside the exact mesh; the flat mismatch
fix does not solve partial-texture hallucination. Main foliage is still painterly
and bright-sign color unresolved. Full correction times are729.92/821.72/826.50s
under concurrent work, not isolated benchmarks. All917,962,668 linear RGB16
channels and12,057,600 native PNG channels verify exactly; sRGB16 agrees within1DN
of independent FP64 with ICC/16-bit metadata checked. Publication copies preserve
all35 JSON receipt bytes. The failed first report assembly and environment-only
audit launch remain archived alongside the successful report-v2/audit-assets-v3
log; neither failure changes image inference or numerical results.
