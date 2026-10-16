# Input-only gain reduces fabric color error, not missing detail

While the isolated ConvNeXt trial runs, tested the existing RawNIND channel
CFA-LS formula on eight already saved CPU predictions: no-context/S at3k/10k,
same fabric/building observations. No new inference, noise, RAW decoding, CUDA
or production changes. The fit reads only predicted RGB and observed noisy CFA;
exact targets are used for subsequent scores.

No-context10k fabric native display PSNR goes25.0211→37.1727dB; S10k goes
31.1956→36.9465. The color shift is visibly reduced, but fine cords remain lost
and corrected3k fabric remains better. Building changes by under.007dB.
This supports further investigation of color consistency; it is not a broadly
validated inference correction or a model promotion. Per-tile fitting/content/
clipping/noise correlation and full-frame behavior remain unevaluated.

The completed private run is `fresh-saved-input-cfa-gain-cpu-v2`; the first
attempt stopped on older metadata using `condition` rather than `conditioning`
and is explicitly marked incomplete. All eight completed native triplets were
viewed, SHA-verified and copied without resizing. Independent phase-wise dot
products rebuild all24 gains within1.03e-14. Published the report and complete
receipts at `docs/saved-input-cfa-gain-cpu.md`.
