# Separate remaining fine-detail bias from noise variation

Recorded: 2026-11-18T11:29:50-08:00 (America/Los_Angeles).

The 64-photo matched panel closes all 512 declared batches with
five EMA candidates. All source pairs and all Bayer layouts use
the same observations. Twenty-four input regeneration checks
pass. The CUDA ADC results agree with the archived CPU controls
within 0.000006 dB on the five verification batches. The two
near-ADC postprocessing report writers initially tried to emit
NumPy integer counts. Normalizing the counts to JSON integers
preserves the original predictions and viewed crop bytes.

On faint ISO6400, 100k lowers weak fine RMS from 12.51 to 11.75
DN16 versus V120. Signed response stays near 12%. Independent
draws attribute about 95% of the MSE decrease to noise-to-noise
variation. The bounded tiny-noise lift lowers 100k fine RMS from
4.41 to 2.96 DN16. The matched near-ADC branches give nearly the
same corrected results.
[Full report and native triplets](../docs/full-corpus-faint-noise.md).

The published photo boards were viewed with the two original source
IDs at fixed native coordinates. Both existing standing photo
families were also re-viewed. The main sky stays smooth and
the fine cab weave stays incomplete. The active phase of the
separate broad full427 collectors remains unresolved.
[Main review](../docs/gfx-qualitative.md) ·
[Cab review](../docs/gfx-green-mesh.md) ·
[Primary score history](../docs/performance-history.md).
