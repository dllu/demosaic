# Validated optional FP16 refinement inference

Added runtime-only FP16 RGB correction convolution selection, exposed through
CLI, paired/synthetic suites and qualitative reporting. Default stays IEEE FP32;
physical maps/high-pass/noise scaling stay FP32, CPU stays FP32, checkpoint
configuration/weights and training unchanged. Added correction-only diagnostic
benchmark with archived source/weights, native synthetic-GT crops and receipts.

Default V16 math is bit-identical to archived preceding model.py on9,437,184
RGB values, fourCFAs and three noise/highlight conditions. Full178 tests passed
in24.87s including CUDAhalfoutput and exactzero-noise checks. Ruff passed.

Completed both real development panels and full427photo+16procedural quality
panel. Max scene-mean primary shift0.000083dB, fullphotoPSNR−0.00000454dB.
No quality improvement claimed. Current protectedfinal test unused.

NewDSCF3879 101.996MP outputs generated in both modes, allRGBuint16. Single
successive shared-machine timings36.39s FP32 correction /26.81s FP16 correction,
0.840/0.708GB CUDApeak (not total RAM). Not idlebenchmark; target10sec remains
unmet. Fullencoded comparison over305,987,556 values per file: linearcameraRGB
RMS0.2163/max7codes; sRGB+2EV RMS1.4667/max197codes. Physical/sRGB difference
is reported honestly, no claim of16bitpixel identity. DefaultGFX/README crops
remain the FP32 correction mode. Eight-sample alternating branch benchmark
median224.66/144.46ms excludes Bayer/DINO body and can include contention.

Evidence, nativephotoGTtriplets, commands and limitations:
`docs/refinement-precision.md`, `docs/results/refinement-precision-v16.json`.
