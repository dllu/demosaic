# Separate repeat error within each noise coupling law

Recorded: 2026-11-18T14:54:38-08:00 (America/Los_Angeles).

Evaluated the frozen paired head and both full-model controls on
all 64 original photos at ISO6400. Each within-pair noise law now
has three independent complete draws with identical clean targets.
Shared fine-increment error drops 301 DN16² with coupled noise and
295 DN16² with independent noise versus Corpus 100k. Between-draw
variance drops 39 DN16² for coupled noise and rises 405 DN16² for
independent noise. The positive response gain and independent
increment loss reproduce across the same-law redraws.

The three new heads are still training. This measurement belongs
to their frozen starting checkpoint.
[Same-law repeat report](../docs/paired-repeat-stability.md#starting-model-on-64-photos-with-three-redraws) ·
[Source metrics](../docs/results/paired-repeat-stability-v2/start64-summary.json).
