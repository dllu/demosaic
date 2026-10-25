# Queue native camera development comparisons behind V119

Recorded: 2026-10-25T13:10:32-07:00 (America/Los_Angeles).

Queued the first model comparison on the previously prepared native-camera
development inputs. This adds a camera-RGB check for the cleaned-corpus quality
work while the original V119 run continues. The hot-pixel/linear-DNG work is
already merged; current useful V114/V115/V117 choices remain documented.

The new controller waits behind the exact original V119 training, eight-stage
endpoint evaluation, independent audit and three saved-output contrasts. It
resolves only their completed final 20k immutable V119 checkpoint. The old
V114/V115/V117 immutable weights and model hashes come from completed photo
receipts; RawNIND preupsample uses its existing fixed CFA-channel adapter. No
intermediate V119 checkpoint is read or evaluated.

The frozen plan declares 1,200 first model calls on new inputs: five methods
times 240 stored observations, including 960 DINO encoder and 240 RawNIND
network calls. The 20 fixed contexts come from 11 held-out CC0 captures, with
three declared physical-noise priors and four CFAs. Their canonical camera-RGB
references are used directly, without inverse-camera unprocessing or fresh
noise. Reference/source identity and training exclusions retain the scope
documented in the input-preparation receipts. Camera models or unidentified
places may overlap; these are low-noise reference estimates, not noiseless GT.

The collector retains exact native FP32 predictions/supervision, actual input
fingerprints, model/encoder hashes and call accounting. CPU-only NumPy64 analysis
reports camera/sRGB PSNR, chroma/gradient error and unclipped camera errors.
Repeated CFA/ROI cases average within capture before equal-capture means and
matched bootstrap intervals. Target-only local DCT bands describe recovery of
the reference's fine contrast, including any residual reference noise; overlap
adds no independent sources. Ten native 160px triplets and twelve full boards
are planned. Viewing and interpretation remain required.

The actual frozen preflight passes closed-form camera/sRGB metrics and a fixture
where equal-capture change is zero while incorrect case pooling gives +0.5.
Live endpoint, changed owner and changed plan rejection all pass before any
execution plan or checkpoint resolution. All frozen Python sources compile;
CPU imports stay free of Torch. Nested matched-contrast receipts are handled
without flattening away their bindings.

At the recorded launch, controller PID 3344479/create 1792958974.73 is idle,
without children, with about 36.5MiB RSS, two CPU cores and nice 10. Its status
waits on the original training controller. No new neural calls, noise draws,
RAW decodes or optimizer updates have occurred. V119's original worker is
still live; the public launch observation sees step 8,250 with finite loss.
The new queue cannot race the original review chain for GPU ownership and
preserves failures without automatic retry.

The public guide, README link and training guide now describe the actual queue.
No new model-quality result or recommendation is claimed. Once the full V119
results and native comparisons are ready, update current documentation with
their strengths and remaining weaknesses.

- [Queue and frozen preflight receipt](../docs/results/native-camera-development-queue-v1.json)
- [Current native-camera guide](../docs/native-camera-development.md)
- [Queue implementation](../scripts/queue_native_camera_development.py)
- [Collector and CPU analysis](../scripts/evaluate_native_camera_development.py)
