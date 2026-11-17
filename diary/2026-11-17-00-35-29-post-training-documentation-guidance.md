# Require concise README and post-training result bookkeeping

Recorded: 2026-11-17T00:35:29-08:00 (America/Los_Angeles).

Expanded AGENTS.md at the user's request with a concise README policy and an
explicit checklist after every completed training run, including regressions.
README should remain roughly 100 lines, replacing outdated summaries and linking
detailed evidence instead of accumulating experiment narratives.

The checklist binds endpoint/checkpoint/training provenance, requires comparable
full-model photo/camera evaluation and PSNR registry/generator/asset updates,
and requires actual native review of both protected GFX fence families with
matched controls. Main-scene sky/building/foliage and both fine-cab ROIs/profiles
remain part of the comparison. Independent ISO100/JPEG references remain
qualitative, never exact GT. Saved baselines may be reused only with matching
inputs, conditioning, checkpoint and display provenance.

Current model/status/gallery guidance must be reconciled, recommendations kept
consistent with the model selector, and incomplete evaluations explicitly labeled.
Historical scores, images and receipts remain preserved. These instructions
change documentation workflow only; no training or evaluation was launched.

Validation: reviewed the instruction changes against the existing repository
workflow, checked referenced paths and `git diff --check`. Other agents' files
were left untouched.
