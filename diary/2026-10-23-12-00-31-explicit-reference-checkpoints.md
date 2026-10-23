# Keep original quality baselines alongside derived initializers

Recorded: 2026-10-23T12:00:31-07:00 (America/Los_Angeles).

The previous goal turn made progress: e5cf1b7 pushed the 1,280-prefix native
source review, separate 90,869-source cohort and prospective matched Tiny/Small
recipes. This turn checked all five original V104/source-scan owners against
their PID creation times. Training, the incoming scan and their waiting queues
continue; no original worker was restarted.

The quality reporting queue now accepts explicit fixed checkpoint references,
separately from the common training initializer. Each binds a label, absolute
checkpoint path, full SHA256, actual step and frozen encoder identity. The
reference JSON and files are frozen inputs. Duplicate labels/files, changed
weights and malformed records fail; references cannot stand in for incomplete
training phases. `V102-zero` labels the derived initializer while original
`V102` retains its actual 20,000-update checkpoint identity. The original model
can now accompany the initializer and both future endpoints throughout reports
and GFX export. Current [reference configuration](../configs/quality-v102-backbone-reference-checkpoints-v1.json)
and [usage](../docs/training-execution.md#fixed-references-alongside-derived-initializers).

New full-frame plans freeze their record validators in a separate operator
directory ahead of an older evaluation queue's helper modules. This avoids
requiring new helper APIs inside an immutable older snapshot. Existing queue
files and numerical sources retain their bytes; older export plans retain their
original module path. A fresh-process test deliberately supplies an incompatible
older helper and confirms that the separately frozen validators load first.

Actual CPU reporting reused the earlier discarded Tiny/Small eight-update
fixtures, plus their zero-gate initializer and original V102: 84 case rows, four
learned models, three classical methods. The queue and evaluator completed with
unchanged weights, encoders, configurations, parameter identities, RNG and
observations; arithmetic reconstructs exactly. All 72 earlier case scores and
all 18 earlier native panels reproduce exactly despite shifted method indices.
No new training updates were performed. V105/V106 remain private discarded
integration labels, not quality endpoints or history entries.

A real negative check declares original V102's step as 19,999. The actual loader
reads the exact original checkpoint at step 20,000 and rejects it before any
learned forward. The v2 receipt records the loaded SHA/step and exact failing
loader frame, rather than accepting an unrelated assertion as proof. The first
negative-check artifacts remain preserved.

The actual export-record selector also returns original V102 and its zero-gate
derivative separately. The public GFX reporter then ran both on the genuine
cached 512-pixel foliage context with original conditioning and shared +2EV.
Four RGB16 TIFFs reopen within .502 DN across all 3,145,728 channel values.
Zero RAF decodes and no CUDA were used; this is not whole-102MP export evidence.
The tested selector and TIFF-inspection functions match the current functions
exactly in AST, while later source-freezing additions are covered independently.

Actually viewed 12 native photographic cells and four GFX cells. Weak umbrella
ribs and cloud texture remain soft; the GFX foliage remains overly smooth.
The independent ISO100 reference is not GT. These checks establish pipeline
integration, not a new quality gain. All 146 targeted reference/backbone/queue/
ADC tests pass, as do Ruff checks. [Actual plans, hashes, results and native
review records](../docs/results/fixed-reference-operator-CPU-v1.json).

At 11:56 PDT the original V104 trainer had passed 8,825 of 20,000 updates and
the CPU scan had flushed 1,792 of 2,395 sources. The prospective V107/V108 plan
still has no training controller. Review V104 and the full incoming tail before
choosing the next useful initializer/cohort. V102 remains the best completed
recommendation; real fine-detail quality and 100MP within 10s remain unmet.
