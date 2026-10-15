# Put the real GFX test beside the synthetic README examples

The README now includes the two existing native 160×160 GFX crop triplets, in
addition to synthetic validation crops. They reuse the reviewed V16 full-frame
renders without resizing. The caption distinguishes original sensor resolution
from binned validation resolution and identifies the ISO100 f/5.6 capture as a
separate qualitative reference, not pixelwise GT. Shared +2EV display and
different framing/aperture/motion are explicit. No new source-disk read or image
generation was needed.
