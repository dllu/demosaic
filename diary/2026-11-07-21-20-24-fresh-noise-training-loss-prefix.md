# Inspect early fresh-noise loss movement without repeating inference

Recorded: 2026-11-07T21:20:24-08:00 (America/Los_Angeles).

The previous turn made concrete progress by implementing and sealing the
independent V178 training/quality auditor with 34 passing checks. At this turn's
start, authoritative process inspection confirms the original V175 training,
completion watcher, V178 admission watcher and matched-trial controller all
remain live at their original PID/create times, with no phase-failure receipt.
V175 is still training; no prefix is restarted or new GPU job launched.

I inspected the first four already audited continuation passes to distinguish
recorded training behavior from hoped-for quality gains. This is a posthoc
descriptive reduction after initial scalar inspection, fixed to the existing
4,000-row prefix/hash. The raw model changes before every recorded update;
fresh sensor draws, model state and learning rate all change together. The
three clipped photo rows per pass retain their observations. These are not
evaluations of four fixed checkpoints or independent scene replications.

Mesh pair-difference mean falls from 0.189038859 to 0.188860525, only 0.094%.
Weak-texture and photo pair means rise 0.059% and 0.156%. Standalone-flat anchor
falls 0.558% and mixed anchor falls 0.976%, while photo flat-anchor rises 4.797%.
The weighted total changes remain small: mesh −0.204%, weak −0.039%, photo
+0.156%, flat −0.387% and mixed −0.589%. These numbers do not establish any
native detail or sky improvement. The photo-versus-flat anchor difference
reinforces the need to compare their separate actual quality costs.

Pre-clip gradient norm exceeds 1 on 59.61%→46.91% of mesh updates and
52.53%→45.45% of weak updates, versus 9.81%→9.81% of photo, 1.42%→0.71% of flat
and zero mixed updates. These are aggregate norms, not per-objective gradients.
The scalar component shares cannot identify gradient or Adam-update influence.
Batch means mix multiple contrasts. Flat-anchor is a clean-mask-weighted
pseudo-Huber objective at 16-DN16 units, not flat-region RMS or a sky score.

The standalone CPU reducer verifies all 3,600 reported seven-term FP32 totals
exactly and 350 means through independent Decimal arithmetic. It publishes
all 20 pass/domain summaries and 50 first-to-fourth field comparisons, with
matched scene bindings, changes and quantiles. It imports neither Torch nor
rawpy, loads no checkpoint/NPZ/source image, performs no neural or sensor work,
and changes no model, training objective, LR schedule or queued experiment.
Existing journals, machine receipts, protected scenes and original media
remain untouched. No new performance report or native comparison is claimed.

The final raw/EMA comparison remains the next useful decision point. Keep the
actual V161 detail strength and its quiet/flat costs, V172 balanced matching,
V173/V174 quiet gains and V171 standalone-flat strength visible. The guide now
opens with those usable choices before implementation-preparation details;
the timestamped diary and experiment pages retain the historical evidence.

[Training-loss table and limits](../docs/fresh-noise-matching.md#four-pass-training-losses) ·
[Complete reductions and source](../docs/results/v175-four-pass-training-loss-v1.json).
