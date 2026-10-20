# Avoidable physics work: exact CUDA outputs, lower component medians

Both deferred CUDA probes completed after the exact spectral inference,
closure, reference and package owners exited successfully. The physical-feature
probe then waited for the exact successful inverse-probe owner exit. These
isolated generated-field checks did not enter the spectral quality comparison.

The [inverse cleanup](vst-unused-inverse.md) skips an unused closed-form inverse
when the expectation-table path replaces it. Across four shot/read profiles
and native64/512, all3,194,880 output values and sampled input-gradient bytes
match the archived original. CPU/CUDA RNG stays unchanged.

|Shot / read variance|Native64 original→candidate, ms|Native512 original→candidate, ms|
| --- | ---: | ---: |
|.001 /0|.22544→.15757|1.82390→1.17299|
|.00256 /.0000262144|.21869→.15802|1.82928→1.17328|
|.00146358 /.00000107157|.22429→.15709|1.82272→1.16880|
|1e−10 /.0001|.22269→.16048|1.82298→1.17040|

The [physical-feature cleanup](physical-feature-unused-work.md) avoids discarded
log-noise fields and a second21-channel concatenation on the anchored path.
All six returned tensors match in both bytes and strides in four B4 cases:
59,637,792 values across native64/512 and both layouts. CPU/CUDA RNG is unchanged.

|B4 native size / layout|Original median, ms|Candidate median, ms|
| --- | ---: | ---: |
|64 contiguous|.82451|.81286|
|64 channels-last|.80477|.78717|
|512 contiguous|5.05994|3.87238|
|512 channels-last|5.10237|4.04150|

Each cell is five alternating CUDA-event samples after two warmups per method
on the shared GB10. The preserved raw samples show variation; these medians
are not confidence intervals or guarantees. The inverse uses IEEE FP64
physical arithmetic/F32 return. Feature construction uses IEEE FP32 with the
unchanged FP64 anchors. Inputs are deterministic nonphotographic all-CFA
fields, with mixed noise families in the feature probe; no camera calibration
or held-out quality inference occurs.

These checks establish tested component parity and timings. They do not measure
a neural forward, optimizer, training throughput, full-frame peak memory or
100MP latency. The existing genuine-weight CPU model/output/gradient checks are
separate evidence. No new model promotion or full-model speed claim follows.

[Complete inverse results](results/vst-unused-inverse-CUDA-v2.json),
[complete physical-feature results](results/physical-feature-work-CUDA-v1.json).
The frozen plans, executed sources and successful owner records remain in
`/mnt/external/demosaic/experiments/vst-unused-inverse-CUDA-v2/` and
`/mnt/external/demosaic/experiments/physical-feature-work-CUDA-v1/`.
The full project quality and100MP/10s requirements remain unmet/unproven.
