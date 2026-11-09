# Review physical cross-scale CFA quality

Recorded: 2026-11-08T18:11:11-08:00 (America/Los_Angeles).

Both V200 endpoints completed all 822 matched inputs. The quality audit,
eleven-method reduction, two strict exports, directional breakdown and native
rendering completed with zero return codes. This publication work used saved
arrays and outputs; no scientific prediction prefix or training was restarted.

EMA response is 11.101842712% of exact GT amplitude, down 0.503164% versus
V198 EMA (79 up / 177 down). Quiet spatial RMS falls 0.059153% / 0.119316%
at ISO6400/12800 (31/32 better). Fresh-flat full RMS falls 0.022330% /
0.030108% (all 48 better). Absent RMS falls 0.047010% on all 256, and present
blank RMS falls 0.028092% on 250/256. Present full RMS instead rises 0.025721%
despite 170/256 lower errors. Natural full-error means improve only
0.000463–0.001555%, with 125/128 better. These are small useful quiet/flat gains
at a slight response cost, not an overall replacement for V198.

Against V195 Whole EMA, V200 EMA response is 99.143181% higher, but quiet
spatial RMS is 1.091599% / 1.526798% higher on all 32 inputs; fresh-flat RMS
is 0.608976% / 0.761964% higher on all 48. Blank and absent errors also remain
higher on every input. V197 retains lower off-signal costs, V195 avoids the
newer building fringe in these views, and V187 is quieter. V120 remains the
general recommendation.

Actually viewed all 60 figures / 12 triplets in 15 original-detail sheets, plus
the actual browser first screen and both small real triplets. Both V200 states
retain pronounced green/magenta building fringes, flat/photo corrugations and
incomplete fine cab crossings. The synthetic 2302 mesh retains rounded colored
nodes and missing thin segments. On 2309 the near-vertical family dominates;
EMA region A falls from V198's 17.449769% to 17.271605%, while region B stays
near 92.005%. These are Fourier-region projections, not isolated wire amplitudes.

The actual seven-state browser passed 48 boards / 336 method pairs / 1,680
native crops / 129,024,000 exact source RGB channels, state/checkpoint text,
click/key flipping and navigation. The earlier explicitly reused-pixel fixture
remains distinct. All native cells stay 160×160, with identical transforms
across methods. Main DSCF3879/3880 sky/building/foliage/coarse fence and both
DSCF3842/3835 cab ROIs/profiles/JPEGs remain present. Independent ISO100/AHD/JPEG
references are qualitative, not exact GT; both capture families stay held out.

The README and current guides document the quiet/response tradeoff and retain
V198's stronger-response choice. The full comparison includes two small native
noisy/raw/GT triplets and two noisy/EMA/GT triplets, exact checkpoint hashes,
source/ROI/noise/exposure metadata, per-input counts and the visible failures.
The combined fine-detail/clean-flat goal is still open. The next training test
must address edge leakage and noisy-flat false positives without giving up
weak real structure; cross-scale agreement alone did not achieve this.

The intervening user-requested storage cleanup preserved all V200 outputs and
checkpoint bindings. This experiment itself made no new source/noise draws,
parent/DINO forwards, RAW decodes, original/dataz accesses or external writes.
All 107 neural source files retain their prepared hashes.

[Full comparison](../docs/scale-supported-cfa-wave-comparison.md) ·
[Final evidence](../docs/results/v200-scale-supported-cfa-wave-final-v1.json) ·
[Publication verification](../docs/results/v200-scale-supported-cfa-wave-publication-verification-v1.json).
