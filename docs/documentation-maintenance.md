# Maintaining the documentation

The README is an introduction and quickstart. Keep it concise: one recommended
baseline, links to alternatives and current results, setup/inference commands,
and a small representative set of native crops with provenance. Put detailed
experiment findings in a report, not in another paragraph in the README.

## Where each update belongs

| Page | Responsibility |
| --- | --- |
| [Current model](current-model.md) | Available model choices, directly compared strengths/weaknesses, recommendation and evidence coverage |
| [Experiments](experiments.md) | Concise active-work status and grouped completed outcomes; links to individual reports |
| [Research](research.md) | Prioritized questions, literature/design reviews and proposed tests |
| [Performance history](performance-history.md) | Comparable completed primary panels from the checked source registry |
| [Documentation index](index.md) | Navigation by task and actual gallery coverage; no running experiment narrative |
| Individual reports and galleries | Explicit model/checkpoint, panel, budget and evidence cutoff; native comparisons and exact receipts |
| [Diary](../diary/index.md) | Timestamped decisions, execution history and reasons for changing direction |

## When results arrive

- Update the owning report first. State whether training, numerical review and
  actual native viewing are complete separately. Compare gains and costs directly;
  study-specific promotion gates do not prevent documenting useful progress.
- Replace the relevant status row in the experiment index. Change the model guide
  when a useful implementation or recommendation changes. Avoid copying the full
  narrative into every overview.
- For a general-looking gallery, name the models actually shown. If newer output
  is unavailable, state that coverage gap and link to newer reports on other
  panels without implying those panels are interchangeable.
- Add only comparable completed panels to the PSNR history. Four-material means,
  ADC-only means and synthetic mesh amplitude cannot substitute for full427
  scores. Missing results stay missing. Version IDs are experiments, not releases.
- Date current overviews when reviewed. Keep dated/versioned reports as snapshots;
  add a short follow-up link when a formerly pending result has completed.
- Preserve original receipts, hashes, comparison pixels and frozen sources.
  Archive long historical narratives with a scope banner and working links.
  Create diary entries with `python scripts/diary.py new` for local DST-aware time.

Quality reports still require at least two small native 100% noisy/restored/GT
triplets with identical ROI/display and recorded checkpoint/noise/exposure.
Real independent or demosaiced references must be labeled accurately. Both
protected GFX families remain required qualitative checks; cached originals
and training exclusions remain unchanged.

The November 17 cleanup preserved the [previous entry points and plot](history/before-2026-11-17-cleanup/manifest.json).
The new PSNR registry adds V131 from completed saved audits; it does not rerun
models or retroactively relabel old outputs.
