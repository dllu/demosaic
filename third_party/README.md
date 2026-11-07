# Separately licensed materials

This repository's original code uses the root MIT license. DINOv3 weights/code
are distributed by Meta under their [DINOv3 license](dinov3/LICENSE.md), copied
verbatim from official commit `6876159a11b4df116f30f667f8c9888617df0751`.
The optional feature branch uses the official pretrained DINOv3 model, with
attribution to Meta's DINOv3 authors. No pretrained DINOv3 weights are included.

RawNIND reference code/weights are fetched separately into generated external
storage by `scripts/fetch_rawnind.py`, with pinned commit, SHA-256 verification,
author/license files, and provenance. Upstream code uses GPL-3.0; the authors
also offer their model weights under CC BY 4.0. The optional comparison adapter
loads that upstream model as a separate evaluation reference; the network code
and weights are not vendored into this repository or its original MIT source.

Commons training manifests retain each image's own author, attribution, license
and source URLs. Source images and derivative caches are not distributed here.
## Nonlocal RAW comparison

`nonlocal-matchfilter/LICENSE` covers the selected network class definitions
from MIA-UIB/nonlocal-matchfilter v1.0.0, commit
`6df6a79ce128a7741af88ff0f3e9794f9b5e03d4`, included in
`src/demosaic/nonlocal_matchfilter.py`. Copyright 2026 Marco Sánchez Beeckman.
The separately built sampling operator is pinned to
MIA-UIB/deform-neighbourhood-sampling v0.1.1, commit
`ba6c21d34effcb3c3903237704ab58388b86d006`; its MIT notice is retained alongside
the network license. Upstream kernel files retain their embedded Caffe notices.
The released checkpoint is an external training-data comparison, separate from
this project's freely licensed image training pipeline.
