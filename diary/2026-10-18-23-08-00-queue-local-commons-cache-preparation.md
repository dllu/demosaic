# Queue isolated cache preparation after local Commons downloading

The matched V82/V83 study remains live on its original4,000-update schedules.
The connected arm reached logged step3,350; the queued full review still waits
for both arms. Rechecked all486 frozen training/review source files and fixed
data/recipe inputs. No optimizer, schedule, model default, training corpus,
quality criterion, README image or protected-final scoring changes.

The local downloader now has301 originals (2,529,766,749bytes), two in progress
and885 pending. The frozen1,188-source selection remains exact. Its4×/8× cache
payload estimates are9.3972GiB/2.3480GiB. Added a separate preparation worker
that waits for the exact downloader's exit, takes the shared archive lock,
requires terminal source statuses and independently rehashes every completed
original while binding all immutable attribution/source fields.

The worker reuses the existing ingestion and protected-scene operators. CPU
worker count1, nice10, one numerical thread, hidden CUDA,200GiB local reserve
and24GiB available RAM protect ongoing work. Free-space checks run before each
source. Both factors are prepared without changing either the local originals
or source archive. A full cache identity/shape/SHA/attribution/error-partition
audit and rounded4×→2×/direct8× comparison precede the42-reference protected
screen. No source is admitted: cleared training hashes remain quarantined and
new holdouts reserved. Independent duplicate/content/known-series review,
manual content inspection and a separately frozen data recipe remain required.

Eight targeted guard/integrity tests pass in1.14s. The first fixture selection
failed before launching a worker because completed originals were all larger
than its5MB cap. A second fixture independently observed the wait state with
no Torch/CUDA libraries and no children, then correctly failed on the live
archive lock. Retained both attempts. The successful third fixture used its
own lock and two copied real Commons originals, exercised the whole frozen
worker, preserved one quarantine/one reserved hash, and completed both scales
and all42 protected-reference checks. All1,328,802 area samples agree within
one uint16 code; CUDA never initialized. No model inference or training occurred.

Production owner3057802/1792390034.78 is live and waiting, with no Torch/CUDA
libraries or children. Its47 source files and49 inputs pass independent hashes.
Plan SHA25634c7d08202cb5f535ee7c284e55f6a24d50054135689f1245c46c5e10bd39f81.
At observation,252.20GiB was free locally and502.11GiB externally. Receipt:
`docs/results/commons-local-preparation-queue-v1.json`. Actual full preparation
and model quality remain pending; the active global goal remains incomplete.
