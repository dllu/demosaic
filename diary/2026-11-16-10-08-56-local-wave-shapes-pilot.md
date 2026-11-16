# Matching and harmonic shape follow-up

Recorded: 2026-11-16T10:08:56-08:00 (America/Los_Angeles).

The saved-frequency audit finds one lost valid fold match among 196 pilot
patches: the building tile at `[128,0]`. The old minimum-total-distance
assignment selects two invalid pairs instead of retaining a valid pair at
0.25 native bins. The new assignment first maximizes valid pair count, then
minimizes accepted distance. An explicit `matching="legacy"` path preserves
the executed old experiment. Its frozen full-three-prior run is unchanged.

The analytic basis now permits up to four harmonics per directional family;
the matched follow-up compares one against three. Counts are determined from
the initial A-only frequency, capped below radius0.24 and held fixed during
sub-bin refinement. The whole harmonic group is excluded in each conditional
null. Coefficients, color-specific evidence, parent replacement and overlapping
support remain the original procedure. Joint group acceptance does not prove
each constituent harmonic.

Also accept even native frame axes rather than requiring divisibility by four.
Every discovery tile remains divisible by four, and even tile offsets preserve
CFA phase. Positive-noise exact-parent tests actually fit all four boundary
tiles of a native66×70 image under every Bayer layout. This is not a 102MP
integration or speed result.

The frozen development study is
`.cache/experiments/local-wave-shapes-pilot-v1/plan.json`, SHA256
`9abd133ea2ee4f3a462f7165f715a7337b6a2892f3d20472b5b3b7ebddf47e28`.
Its two24-input arms isolate matching, then waveform richness. Legacy H1 first
reproduces all18 saved arrays byte-for-byte on source1/far, main building and
the profile3879 cab context:43 discovery tiles total. Both new arms close all
predictions before new GT/reference analysis. Thresholds0/2/4 and primary2
remain fixed. All original V143 procedural and V120 photographic parent
bindings, RAW/noise, protected scenes, ROIs, JPEGs and display transforms stay
identical. These are reused development sources, not a new independent cohort.

Forty-three focused tests pass with `PYTHONPATH=src:scripts`; Ruff passes.
The initial pytest invocation omitted `scripts` from PYTHONPATH and failed
seven existing script-import tests; the36 core tests passed. The correctly
configured run passes all43. No test-failure receipt was deleted.

Both24-case arms completed and closed before the first new target analysis.
H1/cardinality took142.12s; H3/cardinality took241.60s for196 discovery tiles
each, concurrent with V132 training. Matching-only changes just the building,
with primary local maximum2.16549/RMS0.17891 cameraDN16 relative to legacy.
All wire/material/other real predictions remain bit-identical at all thresholds.

At fixed local threshold2, far mean strong response43.332%→46.884%, weak
2.801%→5.460%; quiet RMS4.025958→4.065917 DN16 (+0.993%) and weak-increment
RMS11.803861→11.891810 (+0.745%). Full RMS improves21.721246→21.708231, while
weak orthogonal error worsens11.414568→11.526401. Source1/far weak response
4.592%→9.822% dominates; source0 changes only1.011%→1.097%. Near-edge response
3.611%→3.814% also costs quiet/increment fidelity.

At nearly matched weak response, H1/t0 reaches5.368% with quiet4.039223 and
weak-increment11.806246, lower than H3/t2's errors. Strong response differs.
H3/t0 extends the tested weak ceiling to8.595% with still higher errors. The
first quality-review draft overgeneralized this as no frontier improvement;
the byte-preserved v2 explicitly limits the claim to the nearly matched
weak-response comparison and retains H3's higher response ceiling. This is not
overall fidelity progress or a Pareto-dominance result.

Both ordinary materials look near their parent. H3 local sRGB changes versus
V120 are bark−0.000316/fur+0.002162dB. All4 ADC-only controls remain exact for
all6 variants in both arms. Sky is bit-identical; fixed main crops retain soft
building, painted foliage and coarse fence. Both cab profiles, both ROIs and
both JPEGs show periodic changes without convincing new complete fine crossings.

The extra maximum-new-change stress view is decisive: native building
ROI[0,334,160,160], exposure4, shows conspicuous new green/magenta bands over
the roof and poles in H3. The largest camera-space change relative to H1 is
277.13DN16. The fixed center building crop misses it. This ROI is selected
post-inference from the correction, uses no reference, and claims no GT at
those extra coordinates. Six such contexts are retained, including unchanged
sky. H3 remains explicit opt-in; H1 remains default, with the independent
assignment fix. More waveform degrees of freedom alone do not resolve this
background/confidence failure. Individual added-harmonic validation and a
better competing background are next hypotheses, not demonstrated fixes.

Actually viewed14 native two-row three-arm comparisons, two H3 noisy/restored/
exact-GT triplets and all6 extra stress boards. Each independent arm audit
reproduces679 scalars/9,216,000 native channels across28 boards. Combined
boards recheck14,131,200 more channels exactly; maximum scalar discrepancy
2.78e−15, zero finite/PSNR discrepancy. Publication preserves37 archives and
76 native boards, sources, plans, receipts and corrected review. No original
prediction/receipt is overwritten. README and model/research/index docs include
both the gain and building failure.

Long-run owners were verified by exact PID+creation time: V132 training at6750,
full analytic panel at497/1152, endpoint reviewer and label-correction watcher
still alive. These are progress observations; none of these jobs was restarted
or signaled. The overarching goal remains active and incomplete.
