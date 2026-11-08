Extending V172 from 900 to **9,000 total optimizer updates**, with 8,073 fresh
sensor batches and newly computed frozen-parent outputs, leaves fine-detail
recovery almost unchanged. **V175 raw offers a small quiet-region error gain**;
the EMA endpoint has different color-bias costs. Neither visibly recovers the
missing fine green cab-fence crossings. V120 remains the general recommendation
and V172 remains the balanced matching baseline for further detail work.

Against V172 EMA, constructed mesh response rises **0.05245% for raw and
0.03338% for EMA**, reaching **3.87922%/3.87848% of exact GT amplitude**, from
3.87718%. Only 138/256 and 131/256 present cases increase, respectively.
These are small descriptive mean changes on the fixed cohort. V161 retains
the stronger learned-detail option and its larger quiet/flat costs; its column
remains beside all newer methods in the tables and native boards.

Raw quiet total RMS falls **0.135% at ISO6400 and 0.269% at ISO12800**: 21/32
inputs improve and 11 worsen. Quiet spatial RMS falls **0.150%/0.058%**, with
29/32 improving, including all 16 ISO6400 inputs. Quiet DC error changes
**+0.044%/−1.471%**. EMA spatial RMS also falls **0.157%/0.077%**, but its total
quiet RMS is almost unchanged at ISO6400 (−0.0009%) and **rises 0.213% at
ISO12800**; DC error rises **0.511%/0.704%**. Keep the raw endpoint's modest
quiet gain available alongside the earlier quiet, detail and flat strengths.

Mesh-containing blank RMS changes **−0.0076% raw/−0.1580% EMA**. In entirely
absent mesh cases it changes **+0.0395%/−0.1272%**. Near-zero signed absent
template means do not establish an absence of invented texture. Photographic
band response falls **0.045–0.245% raw** and **0.048–0.238% EMA** across the four
faint/dark cohort means; band error changes slightly in the favorable direction.
The endpoints therefore do not combine higher natural texture response and
cleaner quiet fields across all conditions.

Native512 standalone-flat full RMS changes **+0.091%/−0.0048% raw** and
**+0.099%/−0.085% EMA** for ISO6400/12800. EMA coarse32 RMS falls only
**0.028%/0.0086%**, with 31/48 individual inputs improving. Raw coarse32 changes
**−0.018%/+0.011%**. These mixed and small changes leave V171's stronger
standalone-flat option useful, with its separate quiet-field costs.

All **60 figures in 15 original-detail sheets** were actually inspected,
including 12 noisy/restored/exact constructed-GT triplets. The ordinary first
mesh crop remains nearly uniform; the second retains one strong orientation
while crossing strands stay weak. Both fine cab ROIs and both conditioning
priors retain soft, incomplete mesh. The main coarse fence is reconstructed,
but foliage and building detail keep similar softness. Normal-display sky looks
smooth in this crop; amplified constructed quiet/flat crops still show colored
grain, broad mottle and casts. The subtle numerical gains do not visibly remove
those failures. ADC bark/fur and plane controls appear unchanged, consistent
with the separate exact checks.

Both protected GFX families, their JPEGs and siblings remain excluded from
training. ISO100 AHD and camera JPEG comparisons differ in aperture, shutter,
motion, exposure and processing; they are qualitative references, not exact GT.
The measured gains/costs are retained without a significance or promotion
cutoff. Reused scenes and coupled cases do not measure blind generalization or
training-seed uncertainty. Longer fresh-noise training alone supplies little
new fine-detail recovery here; the separate V178 phase-evidence trial tests an
additional input path with a matched continuation budget.

## Four-pass training losses

A posthoc reduction of the already audited first four continuation passes
finds **small changes in recorded detail losses**. The table compares means
over the same clean scene rows in passes 1 and 4; these are the changing raw
model's losses before each update, not evaluations of a fixed checkpoint.
Fresh noise, model state and learning rate change together. Three noisy photo
rows retain their original observations. No inference or noise is repeated.

| Domain | Updates/pass | Pair-difference mean, pass 1 → 4 | Flat-anchor change | Total loss change | Pre-clip norm >1, pass 1 → 4 |
|---|---:|---:|---:|---:|---:|
| Mesh | 307 | 0.189039 → 0.188861 (−0.094%) | +0.071% | −0.204% | 59.61% → 46.91% |
| Weak texture | 99 | 0.247964 → 0.248109 (+0.059%) | −0.237% | −0.039% | 52.53% → 45.45% |
| Photo | 214 | 0.314902 → 0.315394 (+0.156%) | +4.797% | +0.156% | 9.81% → 9.81% |
| Flat | 141 | No pairs | −0.558% | −0.387% | 1.42% → 0.71% |
| Mixed edge/quiet | 139 | No pairs | −0.976% | −0.589% | 0% → 0% |

The flat-anchor term integrates a clean-target mask and pseudo-Huber error in
fixed 16-DN16 units. Its mean includes all image elements, so it is neither
flat-region RMS nor a sky score. Its rise on photo batches contrasts with the
fall on standalone flats; one aggregate training total cannot establish both
detail preservation and flat behavior. Reported gradient norms also differ
substantially across domains. Scalar term shares do not establish gradient or
Adam-update contributions, and batch losses mix multiple image contrasts.

The reduction checks all 3,600 FP32 totals exactly and 350 means with independent
Decimal arithmetic. It retains every pass/domain/term summary and paired-row
change counts; repeated scenes and coupled members are correlated, with no
significance or generalization claim. This is descriptive training evidence,
not a new quality result or a reason to select a checkpoint early. At that interim
point the fixed recipe was still running. The final raw/EMA detail, blank,
quiet, flat and real fence/sky outcomes are now reported above and below.
[All reductions and exact source](results/v175-four-pass-training-loss-v1.json) ·
[Reducer](../scripts/summarize_fresh_noise_prefix.py).
