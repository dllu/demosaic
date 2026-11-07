# Packed Fourier phase information

Recorded: 2026-11-07T09:53:37-08:00 (America/Los_Angeles).

Read DFENet primary preprint sections3–5 and6 while the fixed V166 training controller remained live. The paper's November2026 journal issue follows its March2025 preprint. Its separate refinement/suppression paths and local patch inference are relevant, but its Gaussian CFA tests do not establish our physical-noise or quiet-sky behavior. No paper code, weights or dataset were adopted.

Eight own deterministic scalar-mosaic fixtures verify invertible four-phase packing. A phase-aware combination reconstructs every native mosaic FFT bin, with maximum errors4.3247e−17 versus FFT and5.9270e−16 versus an independent dense DFT. Pack/unpack is bit-exact. A low/high native alias pair has identical even-x phase samples and per-phase spectral magnitudes but different cross-phase signs. This distinguishes available information from a learned model's ability to use it. It does not reconstruct unobserved RGB samples or prove restoration quality. No RNG, neural, sensor-noise, RAW or training-data calls.

[Exact source, array fingerprints and primary-paper record](../docs/results/packed-fourier-reading-20261107-v1.json). [Research notes](../docs/research.md#native-frequencies-from-packed-phases). V166's recipe, horizon and fixed review remain unchanged.

