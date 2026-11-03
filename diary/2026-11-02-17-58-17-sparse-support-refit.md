# Sparse support and refitting strengthen the mesh with an uneven spill tradeoff

Recorded: 2026-11-02T17:58:17-08:00 (America/Los_Angeles).

Previous goal turn: progress, committed/pushed `4e661f5` with guarded continuous
frequency fitting. This continuation targets its adjacent-blank spill while
recovering more actual wave amplitude. [Final report](../docs/sparse-phase-support.md).

Evidence root `.cache/quality-20261102/sparse-phase-v1/`. All prototypes, failed
trials, source snapshots, logs, metrics and full outputs are preserved. No access
to `/mnt/dataz`, no new real RAW decoder opens, no training or corpus edits.
Cached normalized RAW/parents, ISO100/AHD arrays and both camera JPEGs are reused.
Original captures remain read-only and standing scenes/siblings stay out of training.

## Initial sparse and support/refit studies

Group-sparse TV minimizes fidelity to sigma16 phasors plus TV and group-L1 norms
shared across the two complex components. ADMM has gradient penalty16, second
split1, cap1024, relative primal/feasible-dual goal1e−5 checked every8. The returned
second-split field has exact zeros. CPU/CUDA agree to ~1e−18 on tested fields;
independent analytic two-pixel TV/L1 and masked-single-free-pixel solutions
verify the objective-gap error bounds. The private masked refit uses the same
solver with an exact zero-outside-support constraint and no group penalty.

Six direct group-L1 settings on128 reused recipes/1024 observations reduced
spill but generally dimmed detail. TV8/group multiplier0.5 retained mean response
with ~28% less blank RMS, but slightly higher texture error. Stronger penalties
erased more real mesh. Four support/refit settings then selected a mask with
TV16/group0.5/power9 and refit it with TV4 or8. Selected TV4 gave development gain
.0486272→.0551277, full error10.284063→10.218916DN16 and added blank RMS
.0464005→.0282501. Weaker supportTV8/refitTV4 had more spill. No new neural calls.

`prototype-v4.py`/`locked-policy-v1.json` froze TV16/group0.5 → power9 mask →
TV4 refit before96 new recipes, seeds2026110700–2026110795. Original frequency
selector, inactive gates, post-power shrink9, cap3, aprons32 and stride128 remain.
Clipped selected windows retain original grid-TV exactly. No GT/reference in
estimation, and Gaussian32 covariance after nonlinear fitting is not calibrated.

## First trial failed a blank-support control

768 actual V143 root/DINO calls, unchanged model/backbone/input/RNG witnesses,
zero new V120 controls or optimizer updates. Same scene level0.02, continuous512
geometry before area2/native256, zero PSF, nominal shot0.00128/read6.5536e−6,
ADC16/black0.03. Exact procedural GT enters scoring only. V143 SHA256:
`96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4`.

The96-recipe trial improved mean response ~13.9% and mean added blank RMS ~13.5%
versus refined TV, but worst blank RMS rose1.517→2.581DN16. In seed0782/GRBG,
blank GT error6.12330→6.50431DN16. Common40× camera-linear detail contrast exposed
a new isolated stripe blob in exact-blank support. This is a real algorithm
failure, not an infrastructure failure. The first full3×101.996MP run and76-module
source snapshot are preserved in `work/` and `full-completion-v1.json`.

That96-recipe set became development for the next rule; it is not held-out
validation for the final algorithm. All original scores/outputs remain unchanged.

## Connected support and a second lock

The false island is a separate229-cell region in one frequency mask, alongside
6132 cells; other frequency components have1168/2489/3267 cells. Four-connected
component minima202=ceil(pi*8²) and805=ceil(4pi*8²) were tested across all224 reused
recipes/1792 observations.805 corresponds to one Gaussian coefficient-noise
correlation-area heuristic, not a false-positive calibration.202 kept the false
island;805 removed it. Development mean gain .05139074→.05138931 is essentially
retained, while added blank RMS .0332443→.0316242 and blank GT error improve.
The known0782 case drops to1.44053 added blank RMS and6.14624 blank GT error;
some boundary leakage remains. Centred real lattice contrast stays stronger.

`prototype-v6.py`/`locked-policy-v2.json` freeze minimum805 before64 further
recipes, seeds2026110900–2026110963. First-trial development is declared explicitly.
The private final evaluator imports the original archived74-module helper tree
whose hashes match the locked baseline functions; the new parent collector has
its own frozen76-module source snapshot. Learned model files/weights are unchanged.
`algorithm-source-v2.json` binds those actual dependencies without rewriting old
policy hashes or confusing dispatcher evolution with learned-model changes.

## Independent final trial

512 further actual V143 root/DINO calls; total this continuation1280 model calls
and1280 sensor-noise observations. All neural integrity witnesses pass. Five
postprocess methods share those same512 actual parents. No multiplied inference
counts for comparison methods. Final present means across256 cases:

| Quantity | Refined TV | Connected support/refit |
| --- | ---: | ---: |
| Template response | .0655287 | .0738991 |
| Native160 spatial error,DN16 | 13.197078 | 13.079337 |
| Full256 error,DN16 | 11.057698 | 10.989280 |
| Added blank RMS,DN16 | .0620682 | .0409886 |
| Blank GT error,DN16 | 6.431159 | 6.430213 |
| Worst added blank RMS,DN16 | 1.43444 | 1.99739 |

Response+12.77%, spatial error−0.89%, full error−0.62%, mean added blank RMS−33.96%.
Worst blank RMS+39.25%;10 blank-GT-error regressions,8 added-field regressions,
one response regression. Maximum blank-error increase .134619DN16,0957/RGGB.
The fresh amplified control shows stronger continuation past the true boundary.
This remains opt-in; grid-TV stays the default inside the optional stage.

41 present cases/14 recipes change;50 recipes and all256 absent inputs retain
parent values. Most very weak recipes remain undetected. Group support is not
confidence. In final fresh data49/57 support solves cap, max gap7.01e−5; all57
masked refits reach target. The original unfiltered control has essentially
identical response but mean blank RMS .0428471 instead of .0409886.

Independent joint10-column solves verify2560 final metric rows, max gain difference
3.03855e−14. CPU versus private GPU covers100,663,296 final values, max3.47e−18.
Public GPU matches201,326,592 final/legacy values exactly, preserving512 old
refined-TV cases. Original WLS/selector/envelope helpers remain unchanged.

## Complete frames, native views and cost

Final76-module source and3×101.996MP outputs are under `work-v2/`, with
`full-completion-v2.json`. All76 modules match public source bytes. Same full
V143/normalizedRAW parents and priors; zero new neural calls, RAW opens or noise
draws for either full run. Both unfiltered and connected outputs are preserved.

| Case | Final seconds | Support solves/capped | Output TV solves/capped |
| --- | ---: | ---: | ---: |
| Main fixed Haar | 538.55 | 704/487 | 1080/56 |
| Nominal mesh | 214.29 | 43/31 | 329/24 |
| Nearby mesh | 534.32 | 702/401 | 1150/77 |

Three contended CPU threads share CUDA graphs, one BLAS/Torch CPU thread each;
separate CPU auditing also ran. No controlled speed ranking or end-to-end timing.
Maximum support gaps .0003628/.0001321/.0010842. These bounded solves are not all
converged; numerical dual gaps are not statistical confidence. Output counts
include masked refits and clipped-window old grid-TV calls.

All192 photo and96 uniform corrections (96/48 per parent) retain values. The same
2.88MP wider sky is unchanged. Old4096 flat-noise and924 large-uniform-window
zero-peak receipts imply unchanged bypass; not fresh reruns or new draws here.
Main/nominal/nearby maximum changes remain8288/11638/12083DN16. Original highlight
color disagreement remains unverified, even though the earlier path is preserved.

30 PNG boards actually inspected via nine unscaled contact sheets: standing main
sky/building/foliage/fence, fine mesh under both priors and both camera JPEGs,
independent ISO100/AHD references, sky/strongest-field views, four final exact-GT
triplets and comparisons, final worst-tail normal/40×, first failure before/after.
Each amplified display shares `empty+40*(value-empty)` before identical WB/matrix/
+3EV; GT-derived empty is display-only. No crop pixels resize. All real references
are not exact GT. Lattice contrast is stronger, especially right, but soft and
uneven below ISO100; main foliage stays painterly and broad quality is unmeasured.

## Publication, failures and remaining work

108 unique relevant tests pass, with five CLI/CFA metadata assertions refreshed.
The actual CLI test declares its neural stub separately from1280 real model calls.
Independent native render/copy audit checks12,134,400 PNG channels. All917,962,668
linear RGB16 values match FP32 clip/round/orientation exactly; full sRGB16 within
1DN16 of independent float64, tags/ICC verified. README and guides use final
comparisons and disclose worse tails; `sparse` automatically refines frequencies.

Initial private prototype-v1 had an import-loader typo, preserved with its failed
log; prototype-v2 fixed it. Report-v1 had a tuple in one JPEG panel and left a
partial native folder; report-v2 fixed that for the first trial. Final report-v3
and its audit are complete. Failed scripts, partial artifacts, first-trial
receipts and full outputs were not overwritten.

V120 stays the general validated model recommendation. No weight/corpus change.
V143 full427/camera quality remains unmeasured. The original sigma16 coefficient
measurement already smooths boundaries; component filtering cannot undo that
forward blur. Direct RAW fidelity or a forward-aware coefficient fit is a useful
next hypothesis for the connected spill, alongside uncertainty calibration.
Incomplete weak detail, remaining false continuation, highlight color, placement
sensitivity and speed remain open. The full goal remains active.
