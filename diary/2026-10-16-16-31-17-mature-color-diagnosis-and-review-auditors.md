# Mature color diagnosis and completed-gate audit tools

Published `docs/mature-color-flat-review.md` and its complete JSON receipt. Five
checkpoints replay the same 32 saved analytic observations on CPU FP32. The
ConvNeXt 10k checkpoint, like the mature ViTs, has large selected saturated-field
mean errors while neutral fields stay close. Its photographic fabric crop looks
better than the older late no-context crop; that does not repair the uniform
field failure. No inference/training defaults or model promotion changed.

Retained 160 full float32 predictions; independent Torch64/NumPy64 reconstruction
checks 960 metrics to 4.45e-16. All ten PNGs actually viewed, all 30 native panels
rerender exact, and ten preview files committed with source/ROI/noise/exposure/
checkpoint records. Four chosen hues and one draw are diagnostic, not a broad
model ranking or identified training cause.

Added reusable completed-gate ConvNeXt artifact and control-replay audit scripts;
extended the existing independent statistics auditor from 1k to the mature10k
gate. Actual golden1k rechecks pass: 113094 score rows / 432 intervals, all120PNG /
35F32 / 12RGB16TIFF, and 100528 control cases exactly replayed. The statistics
auditor rejects the still-live10k gate without writing a premature receipt.
These engineering checks run on CPU and do not interrupt GPU ownership.

At this entry, the V58 owner601329 has completed full427 and analytic evaluation
and is evaluating the full102MP standing GFX pair. The queued genuine nonlocal
reference owner1016386 still waits for actual successful V58 exit; it has not
started a GPU child. Commons downloader3989567 remains live. The broader10k
manual/statistical review and genuine CUDA reference evaluation remain pending.
