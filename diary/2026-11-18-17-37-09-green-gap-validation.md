# Check local RAW support for exterior phase across gaps

Recorded: 2026-11-18T17:37:09-08:00 (America/Los_Angeles).

The exact alias diagnostic separates where phase is estimated from
where delivery is allowed. Twenty held-out ISO6400 sources give
43.95% intact response with the exterior phase and 41.32% with free
phase locally. The exterior fit adds 3.029 DN16 less flat texture and
1.45 percentage points more coherent leakage through exact gaps.
The automatic standing replay preserves the sky and picks low
frequencies in the fine cab. The earlier measured cab frequencies
bring back a visible two-direction lattice on the right, with uneven
coverage and regularized spacing. The local fit also shows the lattice.
Both qualitative references for the cab and the main ISO100 AHD were
reviewed at the original crop scale. [Report and evidence](../docs/green-gap-validation.md).

The full-epoch local worker stopped after update 4,500 at its frozen
RAM floor and restarted from its verified 2,500 checkpoint. The first
942 retry scenes agree byte for byte with the interrupted trace.
Both arms had 5,000 distinct verified visits. The latest numerical and
standing reviews remain at update 2,000. [Training status and receipts](../docs/scene-full-epoch.md#execution-status).
