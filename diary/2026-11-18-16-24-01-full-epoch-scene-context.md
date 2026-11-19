# Start a complete matched whole-scene corpus pass

Recorded: 2026-11-18T16:24:01-08:00 (America/Los_Angeles).

Started two 50,000-update continuations from Corpus 100k EMA. The arms share
the same native scene data, corruption and crop schedule, and the spatial arm
adds aligned complete-scene conditioning. The first shuffled pass reaches
all 90,692 eligible photo IDs at update 45,346. Both arms passed GPU
qualification and completed the first matched production phase of eight
updates. The local arm continued from its saved raw, EMA and Adam state with
global scene index 16. Eight-photo monitoring is queued at 2k, 12k and 25k and
the 64-photo replay at 50k.
[Training design and evidence](../docs/scene-full-epoch.md).

