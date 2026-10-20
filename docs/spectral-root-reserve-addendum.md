# Operational root reserve for the spectral trial

The explicit resource recovery uses a64GiB root-filesystem reserve, replacing
the original128GiB operational floor. Heavy runs, checkpoints and evaluation
arrays are on the external SSD. Its500GiB reserve,48GiB stable launch RAM,
24GiB runtime RAM and24GiB CUDA quota still apply. Root usage at preparation
has over120GiB free; retained experiment/cache evidence is preserved.

This changes controller resource checks and adds failure-time resource logging.
The training worker, retention helper and recipe-preparation functions must have
identical ASTs to the validated previous driver, and all46 training-core modules
remain byte-identical. No model, data, noise, loss, precision, seed, batch size,
warmup, original4000 cosine horizon, final quality criterion or promotion policy
changes. Original files and failure receipts remain intact.

Resume the verified1000 state, not unsaved work. Deduct the failed worker's
active time from the already remaining control timeout; perform only the
remaining3000 retained-trajectory updates. Unretained computation may repeat
and is explicitly not represented as equal total hardware work.
