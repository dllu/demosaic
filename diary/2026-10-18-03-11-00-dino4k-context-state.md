# Check DINO context updates in the preserved4k state

Continued the same matched mixed16 trial. No-DINO10k has completed; DINO
2884352/1792313905.76 is live and has reached5,450 updates /87,200 examples
at the observation snapshot. Training controller2645898, quality2667688,
inference-profile2714232 and EMA2881904 retain their exact creation times.
The last three remain child-free and queued. No recipe, data admission,
production worker or queue changed.

The saved DINO4k checkpoint SHA
1e46c039dddabc5ed08df83dd85cf4f5af6fdc7faa9668fb962d902c88b02dc8
passes the independent CPU state inspection. All865 model and865 EMA tensors
and863 Adam parameter states are finite. Adam counters are4,000; the original
40k horizon, FP32 recipe, source bundle and five manifest/protocol hashes match.
All863 trainable parameter names map to optimizer IDs with matching moment
shapes. All11 trainable context tensors changed in both current model and EMA
since2k and have nonzero first/second optimizer moments. Context mean/std
buffers remain unchanged. The CPU checkpoint reconstruction has a frozen,
eval-mode backbone. This confirms saved adapter updates, not useful feature
contribution or quality, and does not directly inspect the live GPU backbone.

No new model forward/backward, optimizer step or GPU work. The exact DINO
owner was live before/after. Preserved checkpoint bytes and recipe metadata
match their receipts. Private checker and receipt:
/mnt/external/demosaic/benchmarks/mixed16-quarter-dino4k-state-CPU-v1/.
Checker SHA3ee3f527a4a5f897bef5c86b910e6efa0d1adddef3d3f51b450af2e466aa6a61.
Receipt SHAd6df6a6c8b10212b91b1f582cad324afdee70a4b8f6986ba49618ef33ab14c15.
The public receipt is an exact byte copy; all11 context update/moment claims
were checked again from it. Checker Ruff, public reference and whitespace
checks pass. No performance claim or new model promotion. Finish DINO10k and
the queued full numerical/native quality review before the next budget decision.
