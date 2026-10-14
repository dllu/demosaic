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
