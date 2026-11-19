# Fixed camera panels for the matched scene 12k models

The 100k parent retains the highest measured-CFA PSNR on the known-camera
panel. The local-only and spatial continuations fall by **0.02934 dB** and
**0.04909 dB** respectively. The unseen-camera differences relative to the
parent stay within 0.004 dB. Native texture and edge rendering look similar
across the four models. [Checked metric and viewing records](results/expanded-scene-12000-v2/matched-primary-cameras.json).

Both fixed panels are complete. The 24 known-camera batches contain
four scenes, eight captures and 72 crops per model. The 30 unseen batches
contain five scenes, ten captures and 90 crops per model. The collector
uses CPU IEEE float32 and the same canonical camera inputs for V120, the
Corpus 100k parent and both 12,000-update scene checkpoints. Each model
uses EMA. The analysis checks all checkpoint and input bindings and
recomputes every measured-CFA score bit for bit from saved predictions.
The same control checkpoints and inputs reproduce the earlier CPU panel
means within 0.000001 dB. Means balance crops within a capture, both
captures within a scene, then scenes.

| EMA endpoint | Known CFA PSNR | Unseen CFA PSNR | Known AHD sRGB PSNR | Unseen AHD sRGB PSNR |
| --- | ---: | ---: | ---: | ---: |
| V120 | 54.31272 | 54.00872 | 40.13888 | 38.91209 |
| Corpus 100k | 54.33708 | 53.97826 | 40.15768 | 38.87236 |
| Local-only 12k | 54.30773 | 53.97866 | 40.07492 | 38.88290 |
| Spatial 12k | 54.28798 | 53.97485 | 40.07480 | 38.86908 |

Against the matched local-only arm, spatial is −0.01975 dB on known
cameras and −0.00380 dB on unseen. The paired scene bootstrap intervals
for both differences include zero. The independent AHD RGB columns are
auxiliary. The primary metric uses the measured CFA reference mask.
[Training recipe and checkpoint hashes](expanded-scene-spatial12k.md#matched-training) ·
[Camera evidence archive](results/expanded-scene-12000-v2/matched-primary-cameras.tar.xz).

## Native comparisons

All nine predeclared first-crop boards were opened at native size. The
text and diagonal edge in the three-apples scene retain similar shapes
across all four arms. The quiet plates and dark furniture fields stay
smooth. The raised 7D texture stays visible, while the finest ridges and
fine tapestry texture stay soft. Each cell is the same 160×160 native
region `[176,176,160,160]` in its archived 512-pixel field. Noisy Malvar,
model outputs and the independent AHD reference share exposure ×1 and the
same color transform. Case-level noise priors, CFA, crop provenance and
display settings are bound in the viewing record. [Native viewing and provenance](results/expanded-scene-12000-v2/matched-primary-camera-viewing.json).

| Known-camera scene | Unseen-camera scene |
| --- | --- |
| [Plates](images/expanded-scene-12000-primary-camera-v1/known-2pilesofplates.png) | [Three apples](images/expanded-scene-12000-primary-camera-v1/unseen-LucieB_3apples.png) |
| [7D](images/expanded-scene-12000-primary-camera-v1/known-7D-1.png) | [Coulicoco](images/expanded-scene-12000-primary-camera-v1/unseen-LucieB_Coulicoco.png) |
| [D60](images/expanded-scene-12000-primary-camera-v1/known-D60-2.png) | [Tapestry](images/expanded-scene-12000-primary-camera-v1/unseen-LucieB_bedroom_tapestry.png) |
| [Museum](images/expanded-scene-12000-primary-camera-v1/known-MuseeL-CopteArch-C500D.png) | [Stick figurine](images/expanded-scene-12000-primary-camera-v1/unseen-LucieB_stick_figurine.png) |
| | [Expedit](images/expanded-scene-12000-primary-camera-v1/unseen-LucieB_top_of_Expedit.png) |

The matched standing GFX review includes fine cab mesh, coarse fence,
foliage, building and overcast sky. The [full427 photo panel](performance-history.md)
resumed from 1,026 of 3,162 checked canonical cases after a second
RAM-floor stop. [Second recovery receipt](results/primary-memory-resume-20261118-v1/second-memory-recovery.json).
[Standing GFX review](expanded-scene-spatial12k.md#matched-development-and-standing-gfx-review).
