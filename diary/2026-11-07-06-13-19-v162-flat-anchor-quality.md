# V162 reduces grain with detail and bias tradeoffs

Recorded: 2026-11-07T06:13:19-08:00 (America/Los_Angeles).

The original V162 run completed both 1,000-update heads and the full fixed
quality review. All 1,000 control trace rows and raw/EMA/Adam states exactly
reproduce V161 harmonic context. All 1,644 actual control predictions replay
byte-exact before storage adoption. All 88 neural source files remain unchanged.
Only target-anchor weight 0 versus 0.25 changes between current heads.

Quiet spatial RMS falls 4.73–7.73% versus V161 on all 32 inputs at both
endpoints. Total quiet RMS falls 1.68–5.29%, improving 26/32 inputs; six regress
at both endpoints. Maximum matched-control increase is 0.907 DN16 raw / 0.763 EMA.
Mesh response falls 20.28% / 21.53%, to 3.846% / 4.112% of exact GT amplitude.
Actual mesh blank RMS improves 2.28% / 3.30% versus V161, but remains above V143.

Native512 total-flat RMS improves 1.28–2.55% in mean versus V161, with 46/48 raw
and 48/48 EMA cases better. Coarse means also improve slightly, with individual
regressions. Versus V143, all 48 coarse inputs improve at both endpoints, with
mean RMS 0.53–0.67% lower; total-flat means remain 0.21–0.67% higher.

Bias remains unresolved: ISO12800 mean quiet DC increases 3.736→3.916 DN16 raw
and 3.597→3.773 EMA despite less spatial error. Total quiet means remain
11.54–12.21% above V143; 30/32 raw and 31/32 EMA cases worsen. All eight natural
band-response means fall versus V161/V143. ADC photo RMS improves modestly,
while ADC slopes have mixed full/coarse behavior; all 192 constants retain parent.

I actually inspected all 72 primary figures in 18 original-detail sheets. Fine
colored/gridded grain recedes in flat/quiet crops, but broad mottle and casts
persist. Fine cab strands are slightly weaker than V161 and crossings remain
soft/incomplete under both priors/windows. Main sky looks smooth at its fixed
+2EV display without a new obvious coherent pattern; this is not flat-safety
proof. Building, foliage and organic microtexture remain soft. Independent
ISO100 captures and JPEGs remain qualitative references, not exact GT.

156 CPU checks, actual CUDA mask/loss/gradient checks and genuine restored
smoke pass. Four strict final loads and 92 finite Adam states at 1,000 pass.
The independent mask auditor recomputes and matches all 1,000 actual GPU masks
from immutable clean targets. Supervised mean eligibility is 70% mesh, 50% weak,
52% photo, 69% flat and 91% mixed; nonconstant eligible targets retain their
actual weak gradients. Clipping increases from 134→197 of 900 supervised batches.
The audit of 4,686 quality rows checks 40,210 scalars / 476 Decimal reductions;
54,451,200 native RGB channels are independently checked.

All ten original scientific controllers/workers and the independent mask auditor
are terminal. Scientific work is 5,364 head calls / 11,424 image evaluations,
plus ten numerical leaf-output backwards that are not neural forwards. All
1,644 new predictions stay external. V162 makes no new parent/DINO/source/noise/
RAW/original calls. Reserves remain 60/152 GiB local/external plus 0.5 GiB margin;
no prior arrays or receipts are deleted, and `/mnt/dataz` remains unused.

The auxiliary readiness verifier's stale copied diary path and corrected
revision2 are preserved. I also checked terminal completion too early while
rendering was still live; the guard rejected the attempt and the sheet lookup
failed. No viewing was credited. The unchanged guard passed after authoritative
render completion. No scientific stage was repeated or modified.

Retain the anchor as a grain-reduction recipe alongside stronger V161 response,
V158 quiet accuracy, V160 ordinary total-flat accuracy and V157 coarse capacity.
V120 remains the general recommendation. The combined dark-detail/false-structure
goal remains active; this is a useful measured tradeoff, not completion.

[Full report/native comparisons](../docs/flat-target-anchor.md) ·
[Final evidence](../docs/results/v162-flat-target-anchor-final-v1.json) ·
[Publication verification](../docs/results/v162-flat-target-anchor-publication-verification-v1.json).
