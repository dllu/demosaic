# Continuous wave frequencies clarify the fine mesh

Recorded: 2026-11-02T16:54:17-08:00 (America/Los_Angeles).

The preceding goal turn was progress: `1e654c1` committed TV smoothing of local
wave coefficients with lower average blank spill. This continuation tests a
specific remaining mismatch: true wire frequency/angle between FFT bins.
[Final report and native gallery](../docs/offgrid-phase.md).

Evidence root: `.cache/quality-20261102/offgrid-phase-v1/`. All prototypes,
unguarded/guarded full outputs, snapshots, logs and receipts remain preserved.
`/mnt/dataz` was unavailable and untouched. Real normalized RAW/parents, both
camera JPEGs and independently demosaiced ISO100 caches were reused locally;
zero new real RAW decoder opens. Original captures remain read-only and test
siblings remain excluded from training. No training or corpus edits occurred.

## Frequency development and lock

The detector and original inactive global gates stay unchanged. For each active
wave, maximize signed cross-DFT on both measured greens after their original
Hann/affine subtraction, retaining physical CFA offsets. Search±1.5 bins per
axis, initial3×3 grid, at most12 damped Newton steps capped at0.5 bin, four fixed
backtracks, original radial band/positive-fy constraints and2-bin collision guard.
RGB residual WLS is then refit at the selected frequencies. TV itself is unchanged.
This reuses noisy observations; its fitted covariance is not calibrated confidence.

v1 capped active gates at their old values. On the reused64 development recipes,
template gain .0781013→.0790036 and full error11.660408→11.642121DN16, with
added blank RMS .0590429→.0621136. v2 refits active power gates and adds explicit
valid-band/collision checks: gain .0801455, full error11.622273, blank RMS .0642281.
All256 absent inputs bypass both versions. The increased spill is a cost, not a
safety gain. Centred real views looked clearer; regular-grid gains proved smaller.

`locked-policy-v1.json` freezes private `prototype-v2.py` before generating64 new
recipes, seeds2026110400–2026110463. The old73-module source is frozen in the
fresh inference plan; the original equations remain available despite the new
public WLS factoring. A known off-bin carrier recovers its physical frequency
across all CFAs and phase-specific affine backgrounds.

## Fresh results and flat stress

512 actual V143 root/DINO calls: present/absent×four CFAs, unchanged full
model/backbone/input/RNG witnesses. No new V120 controls or optimizer steps.
V143 SHA256 `96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4`.
Same continuous512→geometry→area2/native256 generator, zero optical PSF,
level0.02, shot0.00128/read6.5536e−6, ADC16/black0.03. GT enters scoring only.

Five recipes/16 present cases change under both policies. Across256 present
cases, fixed-bin TV→refined-frequency TV means:

- Gain .0164909→.0171090 (+3.75%); spatial error10.103725→10.086485DN16.
- Full error8.958636→8.945854DN16 (−0.14%).
- Added blank RMS .0263240→.0285730DN16 (+8.54%); blank GT error6.412643→6.412800.
- Worst per-case added blank RMS1.94044→1.95296DN16. Seven cases worsen blank
  GT error and two lose gain. Largest blank-error increase .040418DN16,420/GRBG.
- All256 absent inputs retain every parent value. Most weak recipes still bypass.

The fresh23 searches use424 evaluations, max displacement .781123 bin, no
collision fallback.19/23 TV solves cap at1024; maximum relative gap6.11277e−5.
An independent joint10-column solve verifies1536 metric rows, max gain difference
1.10433e−14. Public CPU versus private GPU on100,663,296 fresh values differs at
most3.46945e−18. On512 reused inputs, all original WLS fits and100,663,296 public
GPU candidate values match exactly. AST verifies the factored WLS prefix/body;
all other selector/envelope helper equations remain unchanged. Twelve earlier
scalar whole-context checks remain within float32 rounding.

All192 photographic and96 uniform correction checks (96/48 per V120/V143 parent)
retain every value. A separate4096 fresh flat-noise stress spans8 levels .0001–.3,
2 priors,4 CFAs,64 draws each, with tint[.8,1,1.2], Poisson/Gaussian/ADC16/black.03.
No frequency is selected in any case. This uses an exact flat oracle parent, not
4096 neural calls. Empty detection implies bypass for any finite parent. Total
new noise observations are4608, of which512 have actual model inference. No
universal false-positive or flat-safety claim follows from these bounded checks.

## Full-frame failure, safeguard and rerun

The first complete3×101.996MP run is preserved under `work/`, with74 frozen
modules and `full-completion-v1.json`. Real mesh changes were modest and uneven.
The main sign had a much larger added field: max29,572DN16 versus grid-TV8,288;
main whole-frame added RMS92.9585 versus31.9597. The native strongest-change view
showed increased green/color changes. This was a real full-frame failure absent
from the dark procedural tests, not a failed infrastructure job.

The largest excursion is green at native[c=1,y=1799,x=2821], parent .680826→
unguarded1.132069. All four contributing regular windows contain hundreds or
thousands of upper-clipped observed samples. A linear sinusoidal likelihood is
unsuitable there. The final safeguard retains the original frequencies, gates
and TV fit whenever any observed sample in a selected window is>=1−1e−7.

`saturation-policy-v2.json` explicitly records that this guard was selected AFTER
the unguarded fresh results and full real inspection. All512 fresh dark inputs
are unclipped. An AST/predicate audit proves their100,663,296 output values and
scores are unchanged; this is not prospective guard selection/quality validation
on saturated images. All16 CFA/clipped-phase fits retain original WLS exactly,
and the actual correction test verifies equality to grid-TV. Prior grid-TV
highlight color remains unverified; this only avoids new frequency excursions.

The guarded rerun freezes74 current modules under `work-v2/`, all byte-identical
to public source, with `full-completion-v2.json`. Same complete parents/RAW/priors,
zero new neural calls, RAW opens or noise draws for either full run:

| Case | Refinement s | Frequency searches | Clipped selected windows | TV solves/capped |
| --- | ---: | ---: | ---: | ---: |
| Main | 475.021 | 1101 | 484 | 1080/472 |
| Nominal | 220.606 | 44 | 548 | 329/53 |
| Nearby | 470.180 | 1093 | 554 | 1150/414 |

These are contended3-thread CPU jobs sharing a float64 CUDA graph solver, not a
controlled speed ranking or fresh end-to-end neural timing. Max relative TV gaps
remain .000353433/.000294953/.000450743. Maximum added fields return exactly to
grid-TV8,288/11,638/12,083DN16. The three original failed160px sign ROIs now match
grid-TV exactly; all failure/source/output receipts remain preserved.

## Native publication and verification

29 boards actually viewed through seven unscaled contact sheets. Main sky,
building, foliage, larger fence; fine mesh under both priors; both camera JPEGs;
three wider-sky views; strongest changes and three unguarded→guarded controls;
four fresh exact-GT triplets plus five-way comparisons. Source/ROI/checkpoint/
noise/WB/matrix/exposure are bound per panel. Real ISO100/AHD/JPEGs are not GT.

Full-grid lattice differences are modest and uneven, smaller than centred-window
changes; recovery stays soft and below ISO100. Foliage remains painterly. The
same2.88MP wider sky retains every parent channel. Old924 large-flat windows have
zero selected peaks and unchanged selection, giving derived bypass rather than
fresh reruns. Adjacent procedural blank spill remains measurable and increases.

Independent native rendering/copy checks cover10,905,600 PNG channels. All
917,962,668 linear RGB16 values match saved FP32 clip/round/orientation exactly;
complete sRGB16 within1DN16 of independent float64, tags/ICC correct. No resizing.
81 relevant tests pass, including CUDA reuse/RNG, independent TV math, physical
off-bin carriers, boundaries, bypasses, clipping equivalence and CLI/export. The
CLI test explicitly uses a neural stub, separate from512 actual root calls.
Initial test invocation named a nonexistent test file and ran zero tests; its
error log is preserved. Later integration logs contain80 then81 actual passes.

The option is explicit: `--phase-harmonic --phase-harmonic-refine-frequency`.
Fixed-bin TV remains the policy without the additional flag. README/guides and
native comparisons are updated with the gain and costs. V120 remains the broad
validated model recommendation; V143 full427/camera quality is unmeasured.
Incomplete weak-detail recovery, blank spill, original highlight color, uncertain
noise/confidence, placement sensitivity and speed remain open. Goal stays active.
