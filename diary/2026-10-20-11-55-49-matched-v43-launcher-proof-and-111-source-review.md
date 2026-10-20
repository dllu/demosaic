# Verify the matched V43 launcher and review 111 corpus sources

Recorded: 2026-10-20T11:55:49-07:00 (America/Los_Angeles).

The previous goal turn made substantive progress: documentation/PSNR history,
local diary corrections, V43 augmentation controls and actual source curation
were committed/pushed. This turn revalidated the same live source worker and
its new supervisor; neither was restarted. The full ranking remains pending.

Expanded actual visual review now covers111 unique sources:106 retained and
five withheld. Six additional sheets contained36 useful sources; two more
sheets contained12 selected by an explicitly posthoc ADC-linear-error/local-
gradient ratio. The latter chiefly selected legitimate smooth skies, saturated
gradients and bright boundaries, not additional bad photos. Native grain alone
is not an exclusion when the actual8x target remains useful. Across all rounds,
21 contact sheets and six larger native1024 crops were actually inspected.
Original source bytes and historical manifests remain untouched.

A matched launcher is implemented for the original V43 architecture, with
small curated cohort, larger curated cohort and larger fine-detail recipe.
The production path requires final completed curation, exact V43 parent/native/
paired/validation lineage, CPU and discarded CUDA/B16/native256 checks, then
three fixed20k stages with fresh optimizers. It uses the final20k EMA as the
primary endpoint and retains diagnostic4k intervals. No production plan or CUDA
training stage has been launched while final ranking/review are pending.

The first discarded CPU launcher proof completed24 updates per arm. A second
source freeze adds explicit authorized-cache environment, original manifest
checks, exact permitted recipe differences and fresh-optimizer checks; it also
completed all72 actual updates and exited successfully. Independent saved-state
checks verify71 model/71 EMA tensors,69 Adam states, finite values/counters,
identical final Python/CPU/CUDA RNG states, and the source archive differences.
V93/V94 preserve all15 shared paired/native observations and change five Commons
observations; V94/V95 preserve all10 paired observations and change six treatment
observations. CPU/B1/native32 and provisional memberships are engineering only,
not final curation, CUDA evidence, quality measurements or timing results.

Latest manual decision set:
`.cache/quality-first-20261020/manual-source-quality-decisions-v4.json`.
Launcher proof plan SHA256:
`3d249b040db52fab85be351568c0d1358aa0bb190dc96169b944b95bbfc9d24c`.
See [the quality study](../docs/quality-first-training.md) for public receipts.
The full PROMPT quality, real-photo superiority and100MP/10s requirements remain
unproven; speed work remains deferred at the user's request.
