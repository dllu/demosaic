# Phase profiles improve lower-noise wire response

Recorded: 2026-11-17T11:11:53-08:00 (America/Los_Angeles).

The previous turn made progress with donor geometry and the long-run epoch
audit. This turn tested a richer shape above the same RAW-supported guide,
scored the results, and qualified analysis of the broader faint-photo panel.

The [phase-profile study](../docs/guided-phase-profiles.md) compares a sine
wave against eight circular knots fitted from the query's own same-color
samples. Both use the same two donor frequencies, parent and nuisance fit.
Discovery and withheld validation use opposite query folds. Original guide
coordinates and threshold values remain fixed. The comparison uses draw 1,
all four Bayer layouts, eight reused geometries, two placements, two noise
profiles and three independent query roles per group.

At ISO400 far and threshold 2, the phase profile raises signed weak response
from 4.235% to 14.330% and strong response from 44.261% to 59.152%. Weak
increment RMS falls from 10.08948 to 10.03998 DN16 and query quiet RMS rises
from 2.49215 to 2.50075 DN16. Five of eight geometries improve their paired
increment error. Phase threshold 4 still has a small benefit at almost the
same quiet error as sinusoid threshold 2. ISO6400 weak response is essentially
flat at conservative thresholds, with higher increment RMS. Removing most
shrinkage increases quiet and increment errors.

Four synthetic and eight real comparison boards were opened, including
both standing capture families and both cab conditioning profiles with both
JPEGs. The phase guide leaves the standard sky and building ROIs unchanged.
Coarse-fence modulation increases a little, foliage remains soft, and cab
crossings remain incomplete with some diagonal striping. ISO100 AHD and
JPEGs remain qualitative references. Protected captures and siblings stay
outside training. No model forwards or new RAW opens were needed.

All 896 metric rows pass the 15,232-reduction independent audit. All 48
adopted camera panels reproduce exactly. Four native triplets are exact
subsets. The threshold-sweep plot was inspected, and the executed originals
and caption-only revision were archived. All 90 focused local-wave and ADC
tests pass, as does Ruff.

The four-policy [faint-photo report](../scripts/report_full_faint_photo_panel.py)
uses original-source contrast and eligibility masks, 16×16 native block
DCTs, exact faint target projections and equal source weights after four-CFA
pooling. Its qualification processes four batches and 128 policy rows,
cross-checks independent DCTs and exact ADC re-encoding, and exercises two
native comparison layouts. The two qualification versions have identical
score rows. Scoring waits for the full 428-batch collection receipt. The
existing study is live at 131 of 428 and the analysis worker is waiting.

The long trainer was verified live at 19,325 updates. The 110-case milestone
review still waits for its retained 20k receipt. The two primary photo
collections continue at 437 and 619 of 3,162 respective cases. There is no
new full-model chart point or recommended-model change. The synthetic profile
gain moves the weak-detail work forward, while high-noise and real-scene
fidelity remain unresolved.
