# Research diary

Entries are named in **America/Los_Angeles local time**, including daylight
saving time. The filenames sort chronologically within that local clock.

Create a new entry from the repository root:

```bash
.venv/bin/python scripts/diary.py new "Describe the result" --slug short-summary
```

The [timestamp correction map](timestamp-corrections.json) records84 older
entries whose filenames accidentally used UTC. The migration converts their
original instants and preserves every Markdown byte. Machine-generated
receipts retain their original, explicitly labeled UTC timestamps and literal
historical paths. Resolve an old diary path without editing such a receipt:

```bash
.venv/bin/python scripts/diary.py resolve diary/OLD-FILENAME.md
```

For a concise view of the evidence, start with the
[experiment index](../docs/experiments.md) rather than the chronological diary.

Latest completed cohort reviews: [full wave panel, V131 broad audit and fixed ADC repair](2026-11-16-11-25-42-full-panel-v131-audits.md).
V131 photo+0.04000 dB has unseen-camera/ADC-color costs; an opt-in physical ADC
repair adds0.15074 dB ADC-photo PSNR while increasing weakest-band error1.43%.
V132 production continues on its original full20k schedule.

Latest matched progress: [V1321k attention review](2026-11-16-08-22-36-v132-progress1000-review.md),
small faint gain versus V1311k, still below V120; no clear new real mesh crossings.

Latest fixed-basis diagnostic: [target-assisted measured-wave fits](2026-11-16-08-49-09-measured-wave-oracle.md),
weak response 9.43%→19.39%, with quiet/increment errors worsening on most views;
an oracle result, not an inference improvement.

Latest input-only comparison: [phase-aligned measurement aggregation](2026-11-16-12-46-37-phase-measurement-aggregation.md),
two-source400/far weak response2.80%→12.68% versus H1, with quiet/increment
error+5.44%/+1.94%, severe building bands and poor high-noise results. Both
projection arms are fully reviewed. A four-forward A-only neural nuisance
diagnostic improves held-out sensor prediction, with blur/artifacts remaining.
The separate [complete local-support panel](2026-11-16-11-25-42-full-panel-v131-audits.md)
retains all eight sources/CFAs/repeats and its smaller measured tradeoff.

Latest consolidation: [shared experiments and composed models](2026-11-15-22-22-09-experiment-consolidation.md), with exact V200 CUDA-prefix replay and preserved historical evidence.

Latest research: [weak-detail literature review and reconstruction ideas](2026-11-15-23-04-10-weak-detail-literature.md), documenting proposals without implementation.

Latest experiment: [matched shared-edge trial launched](2026-11-16-01-38-52-shared-edge-trial.md); trained quality pending.

Latest diagnostic: [withheld CFA evidence and predictable edge leakage](2026-11-16-01-46-42-withheld-cfa-edge-diagnostic.md).

Latest follow-up: [edge refinement and completed shared-edge training](2026-11-16-02-02-45-edge-refinement-and-training.md); EMA/native quality review pending.

Latest quality result: [shared-edge raw/EMA review](2026-11-16-02-16-07-shared-edge-quality.md); small quiet gains, weaker mesh response and persistent artifacts.

Latest test: [fresh independent-noise finite wires](2026-11-16-02-41-09-near-edge-response.md); nominal panel complete, lower-noise profiles running.

Latest model trial: [completed noise ladder and competing-orientation training](2026-11-16-03-37-19-competing-phase-training.md); 900 updates complete, raw/EMA/native quality review underway.

Latest quality review: [competing-orientation raw/EMA and all60 native boards](2026-11-16-03-58-23-competing-orientation-quality.md); local weak-sector gain, lower aggregate response and persistent artifacts; conditional-noise review running.

Latest conditional result: [competing-orientation three-noise review completed](../docs/competing-edge-response.md); higher far-edge weak response with strong-direction losses and mixed quiet effects. [Diary follow-up](2026-11-16-03-58-23-competing-orientation-quality.md).

Latest model trial: [complementary CFA branch over frozen V200 EMA](2026-11-16-04-38-49-complementary-cfa-branch.md); training live, exact baseline review and all three conditional-noise profiles queued.

Latest trial status: [complementary training completed and evaluator repaired](2026-11-16-04-38-49-complementary-cfa-branch.md); all 900 updates audited, corrected raw/EMA quality review running without retraining.

Latest fine-detail follow-up: [additional fine-frequency proposals](2026-11-16-20-39-10-fine-frequency-proposals.md), complete48-case/44-figure review. Analytic1600/far weak0.989%→2.037% with unchanged quiet error/slightly lower increment error; source1 drives gain. Cab lattice more visible with purple/green grid, building/neural1600 errors rise. Separate broad-only full guided study remains running with its exact publication queue.
