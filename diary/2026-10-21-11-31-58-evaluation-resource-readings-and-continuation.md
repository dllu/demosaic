# Preserve evaluations during disk pressure

Recorded: 2026-10-21T11:31:58-07:00 (America/Los_Angeles).

V95 continues under its existing recovery worker, through logged step 2,950 at
this observation, with finite losses and gradients. V93/V94 are complete; full
quality evaluation remains gated on the final V95 endpoint and owner exit.

Prepare the evaluation controller for the same resource-failure class. Log exact
RAM/free-space/mount readings, suspend only an owned worker for disk-only
shortages, and continue the same PID after stable original launch thresholds
and a fresh frozen-input guard. Keep active RAM 24 GiB, launch RAM 48 GiB,
root/external production reserves 64/384 GiB, stable interval 60 seconds,
disk wait 7,200 seconds and per-stage wall limit 43,200 seconds. RAM breaches
still terminate the worker. Freeze the shared recovery helper when preparing
the future evaluation. No automatic retry is introduced.

Three actual CPU worker tests with controlled resource readings pass: the
counter stops and resumes under the same process identity; changing a frozen
input while stopped prevents continuation; and a RAM-floor breach preserves
the exact reading without taking the disk suspension path. Test workers exit
or are cleaned up under their original ownership. These are process-control
checks, without model inference, CUDA or a naturally occurring resource breach.

The numerical evaluation worker and native-triplet validator have unchanged
syntax trees relative to commit b9f276b. Ruff check/format pass. The
[resource-control receipt](../docs/results/v43-quality-evaluation-resource-control-CPU-v1.json)
records source, tests and result hashes. Full production branch execution,
independent metric audits and actual native crop review remain ahead. V43 is
still the working reference; quality comes before speed.

