# Matched phase evidence: small mesh gain and quiet-field costs

Recorded: 2026-11-08T01:14:44-08:00 (America/Los_Angeles).


Both actual training arms, the four-endpoint review and controller are terminal.
Control and evidence each completed1,000 cached rows/900 updates/3,600 noisy
images from V172's real raw/Adam/EMA state. Existing network clocks are1,800;
the new adapter clock is900. All ten checkpoints, both full traces, clean masks,
1,800 FP32 loss totals, EMA/frozen tensors and genuine row8 restoration pass.

The independent quality audit passes3,288 durable rows/13,152 input fingerprints,
144 native RGB plus144 residual arrays,107,544,576 addition channels,1,164
recomputed metric scalars,556 Decimal means and750 input-only raw/EMA evidence
pairs. All3,288 exact frozen replays and288 ADC identities pass. The review
made3,288 wrapper/frozen,3,000 matching,15,000 sampler and1,500 projection calls.
No new parent/DINO forward or sensor-noise draw was used.

I made a launch error for the first manual quality audit: resolving the venv
Python symlink selected /usr/bin/python3.12,which lacks Torch. It exited at
import before model/audit data work. Its launch/log and claim remain intact.
The second launch used the explicit .venv/bin/python path and unchanged frozen
auditor; it passed. No scientific forward,noise or successful result repeated.
[Execution provenance](../docs/results/v178-completion-execution-v1.json).

Evidence raw/EMA constructed mesh response reaches3.924275%/3.923549% of exact
GT amplitude,versus3.888490%/3.887981% control. Relative gains are0.920293%/
0.914800%,but only121/256 raw and125/256 EMA pairs increase. Against V172 EMA,
response rises1.214548%/1.195809%,with209/256 and201/256 inputs increasing.
Feature measurements and3,120 extra learned weights change together.

Quiet spatial RMS rises versus control at both noise levels: raw0.0413%/0.0110%
and EMA0.0525%/0.0165% for ISO6400/12800. EMA quiet total RMS falls0.0385%/
0.0068%,with DC changes; ISO12800 standalone full-flat RMS rises0.0110%.
Against V172 EMA,the evidence EMA's quiet total falls0.0894%/0.0518%,but ISO6400
quiet spatial error rises0.0518%,standalone full-flat error rises0.1162%/0.0151%,
mesh-present blank error rises0.0625% and absent full error rises0.0509%.
Natural-photo band changes are tiny and mixed. These are reused development
inputs/one continuation,not blind or multi-seed results.

Actually inspected all18 original-detail sheets/72 native figures,including24
unresized noisy/restored/exact constructed-GT triplets. Mesh2302 is almost
uniform at normal display; mesh2309 still loses the weaker crossing. Contrast40
shows broad colored errors in blanks,flats and quiet fields beside edges.
Both cab ROIs/profiles remain weak and incomplete,with no clear new crossings.
Main sky is smooth at ordinary exposure4; coarse fence survives,foliage and
building details stay soft. ADC bark/fur/planes retain frozen output. ISO100/AHD
and JPEG views are qualitative references,not exact GT. Protected captures,
JPEGs and siblings remain excluded from training; originals and /mnt/dataz unused.

Published four strict CPU inference exports,all13 methods/10,686 rows/34contrasts/
714 cells,and72 native PNGs. The matched viewer opens controlEMA/evidenceEMA;
actual Firefox checks48 boards/96 matched pairs/480 crops,raw/EMA metadata,
click/F flipping,navigation and no JavaScript errors. Independent browser pixel
verification checks all36,864,000 RGB channels exactly against source PNGs.
[Browser evidence](../docs/results/v178-native-viewer-verification-v1.json).

README/current choices now retain V178's small mesh-response option alongside
V172 balanced,V173 quiet,V171 flat,V161 stronger detail and V175 raw quiet gains.
At least two current native mesh triplets remain in README. V120 Small is still
the general recommendation; strong fine dark crossings and clean noisy blank
sky remain open. V180 local evidence is CPU prepared and untrained; its local
support fields are the next architectural hypothesis,with seams/spreading and
CUDA cost requiring actual checks.

The final [independent publication verifier](../scripts/verify_phase_evidence_publication.py)
checks exact receipt copies,four exports,all714 cells,all72 PNGs and independently
recomputed new crop pixels,browser provenance and document links. Its result
is preserved as [publication verification](../docs/results/v178-phase-evidence-publication-verification-v1.json).
[Completed report](../docs/phase-evidence-comparison.md) ·
[Exact final evidence](../docs/results/v178-phase-evidence-final-v1.json).
