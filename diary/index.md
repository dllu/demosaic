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
