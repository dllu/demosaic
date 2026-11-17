State of the art 16 bit joint demosaicing and denoising from free images.

See PROMPT.md for additional details.

Keep README and docs current with the best useful implementations and notable
image comparisons. Study-specific significance/promotion gates do not freeze
the architectural baseline or prevent documenting real gains. Compare strengths
and remaining weaknesses directly. Use the timestamped diary for historical
decisions; preserve existing machine receipts and experiment evidence.

Diary filenames and human-facing diary creation times use the DST-aware
America/Los_Angeles local timezone. Create entries with
`python scripts/diary.py new "Title" --slug short-summary` to avoid UTC filenames.
Explicitly labeled UTC timestamps inside machine receipts remain UTC. Historical
renames are recorded in `diary/timestamp-corrections.json`; preserve receipt bytes.

Performance reports for improved models must include at least two small native
100% crop triplets: noisy, denoised, and GT. Use identical coordinates and display
transforms across methods; never resize the crop pixels. Record source/ROI,
checkpoint hash, noise conditioning and display exposure. For real captures,
label approximate or independently demosaiced references accurately instead of
calling them exact GT. Keep a small representative set in the top-level README.

The GFX100S train/platform scene specified in
`configs/gfx-qualitative-20231231.json` is a standing real-photo qualitative test.
Cache those two RAFs locally in `.cache/gfx-qualitative-20231231/` to avoid waking
the source hard drives. Originals remain read-only. Keep this scene and its
siblings out of training. Use DSCF3879 (ISO6400) and DSCF3880 (ISO100) going forward; these replace
DSCF3842/DSCF3883 and have nearly identical framing. Include foliage and
chain-link-fence crops alongside sky and building detail. The ISO100 f/5.6
exposure still differs in aperture and moving subjects; it is a qualitative
reference, not a pixelwise scoring target.

Also keep the additional fine green fence beside the red train's cab as a
qualitative test in `configs/gfx-green-mesh-20231231.json`: DSCF3842 ISO6400 and
DSCF3835 ISO100 f/5.6, with both straight-out-of-camera JPEGs. Cache the extra
media in `.cache/gfx-green-mesh-20231231/`; reuse the existing cached DSCF3842
RAF. Include this difficult mesh in future quality reports alongside the main
DSCF3879/3880 scene. The reference differs in aperture, exposure time and moving
subjects; it is not exact GT. Keep both captures, their JPEGs and siblings out
of training, and preserve original files read-only.

## Keep the README concise

Keep README a quickstart, aiming for roughly 100 lines: project purpose, the
recommended model and its main limitations, setup/inference commands, a small
representative native-crop set, and links to current guidance and results.
Replace outdated summaries instead of appending each experiment's findings.
Do not add a chronological model catalogue, detailed score tables, training logs,
or every new comparison image. Keep the required crop provenance concise and
link the complete report. A new experiment does not automatically need a new
README paragraph; update its recommendation, representative evidence and chart
coverage links when those change.

Put model tradeoffs in `docs/current-model.md`, research status in
`docs/experiments.md`, and detailed findings in scoped reports. Keep
`docs/index.md` as navigation and the diary as history. General-looking galleries
must name the models actually shown and link newer reviews or state the coverage
gap. Follow `docs/documentation-maintenance.md`; preserve historical evidence.

## Bookkeeping after every completed training run

Successful training means a completed run, not necessarily a quality improvement.
Do this bookkeeping for regressions and inconclusive results too. Track training
completion, numerical evaluation and actual native-image review separately;
do not mark a model's quality review complete merely because training exited.

1. **Bind the endpoint and publish its report.** Record experiment ID, parent,
   checkpoint SHA256, training data/recipe, update/example budget and measured
   training duration. Identify raw versus EMA weights and the evaluated inference
   policy. Compare with the matched parent and current recommended model; report
   gains, regressions and remaining weaknesses. Keep training time separate from
   any measured inference time. Preserve original receipts and frozen sources.

2. **Update PSNR history from comparable completed evaluations.** For full-model
   endpoints, complete the fixed 427-photo and known/unseen camera panels used by
   `docs/performance-history.md`. For scoped component/pilot studies, publish their
   own metrics and explicitly explain missing broad-panel coverage. Never insert
   four-material, ADC-only or mesh-response measurements as a full427 score.
   Add eligible endpoints to the source-bound registry in `docs/results/` and
   `scripts/plot_version_history.py`; update its selected studies, default registry
   and coverage notes so a normal rebuild includes the new result. Regenerate
   the CSV, PNG/SVG/PDF and `docs/performance-history.md`, and refresh incoming
   coverage labels. Preserve old registries/receipts and existing measurements.
   Check source hashes, checkpoint identities and panel comparability; inspect
   the chart and run `tests/test_version_history.py` when changing the generator.
   Plot regressions as well as gains; missing measurements stay explicitly missing.

3. **Refresh both standing fence comparisons.** Evaluate the new endpoint on the
   cached main DSCF3879/3880 scene, including chain-link fence, foliage, sky and
   building, and the separate DSCF3842/3835 fine green cab mesh, including both
   left/right ROIs, both established noise-conditioning profiles and camera JPEG
   references. Use the fixed configurations above, identical native coordinates
   and display transforms, and the current baseline/matched parent. Reuse saved
   baseline outputs only when checkpoint, input, conditioning and rendering match.
   For a component model, identify the complete composed parent/component path.
   Actually inspect the native comparisons for missing crossings, false color,
   splotches and flat-region texture; stronger fence contrast alone is not success.
   Publish provenance and update the current review maps in
   `docs/gfx-qualitative.md` and `docs/gfx-green-mesh.md` to link the new report.
   Keep older boards labeled by checkpoint. Independent ISO100/JPEG references
   remain qualitative references, never exact GT or pixelwise scoring targets.

4. **Reconcile current guidance.** Replace the relevant row in
   `docs/experiments.md` and update `docs/current-model.md` with useful strengths
   and costs. If the recommendation changes, keep `configs/current-model.json`,
   README, usage guidance and the chart's reference consistent. Update any
   general-looking gallery or overview that would otherwise imply older results
   are current. Do not imply a GFX review updates the Q2/Sony/GFX50R panel.

5. **Close the record.** Add a local-time diary entry linking the report, chart
   update and both qualitative reviews; check links and commit/push the relevant
   work. If an evaluation cannot be completed, explicitly record what is pending,
   why, and the last evaluated checkpoint in the report and experiment index.
   Never silently carry forward an old score or relabel an old image. Preserve
   other agents' work and keep protected captures and siblings out of training.
