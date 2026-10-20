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
