# Review the first160k-example endpoint on fixed CPU/native crops

Previous goal turn was a verified wait on DINO2884352/1792313905.76. Continued
the same matched trial, with no-DINO10k already complete. DINO advanced from
2,875/46,000 to4,225/67,600 updates/examples during this CPU work, about1.23s
per effective16 update. Training2645898, quality2667688, inference profile2714232
and EMA2881904 retain their recorded creation times. The last three remain
child-free and queued. No source, recipe, data admission or GPU job changed.

Prepared a separate selected CPU preview of no-DINO10k checkpoint SHA
d6e3bc6d98b1ffc294ac651c731636ef4072bef284925f357b690b78cc7fa9c1.
Use the exact trained frozen package and fixed old CPU observations: two
synthetic photos plus sky/building/foliage/fence common32-grid512 GFX contexts.
Only six new EMA predictions, plus a byte-identical first-photo repeat. Reuse30
existing control triplets and their saved F32 arrays; no control network rerun.
Controls: own2k, old RAW40k/equal160k examples, V43, V63, RawNIND CFA-channel.
CPU worker2914581/1792315582.39 completed successfully and exited. Source/model/
RNG/checkpoint bytes unchanged, CUDA unavailable/uninitialized throughout.

Selected photo sRGB PSNR29.97382581/26.48805050: own2k gains1.17410/.48705dB,
but old equal-example RAW40k leads by1.50814/1.85468dB. Working V43 is
40.69080/35.20764; V63 is33.69030/35.76606. These are two fixed ISO12800-prior
CPU observations and240px interiors, not427-source means, confidence intervals
or a causal batch effect. Real GFX references remain independently demosaiced
ISO100/f5.6 captures, not exact GT/no scoring. Contexts are not full-frame outputs.

Actually viewed both native boards with view_image/detail=original:48 exact
unresized160px cells represent all36 triplets. Some grain reduction over2k;
substantial colored grain remains in canopy/sky/building, with soft foliage
and weak noisy fence structure. V43/V63 are markedly cleaner but lose fine
cords/leaves; RawNIND has soft/wavy structure. No decisive new real advantage.
Keep V43 README reference and finish the scheduled full matched review before
choosing a further training budget. No promotion or automatic extension.

Independent saved-array readback replays all108 panel pixel blocks exactly,
checks12 common outer panels and48 unresized board cells. All12 photo scores
match independent float64 fsum reduction with zero difference; cached control
scores unchanged. Renderer reused, so this is not an independent definition of
the color transform. All460 preview input/source guards, including387 frozen
workflow checks, remain unchanged. Eight published PNGs are byte-exact copies:
six new triplets and two boards. Report includes both required exact-GT triplets
and GFX foliage/fence, source/ROI/checkpoint/noise/display metadata and credits.

Private driver/plan/audit/publication:
/mnt/external/demosaic/benchmarks/mixed16-no-dino10k-CPU-preview-v1/.
Execution report SHA55989868025eccea4a5980a9720b03f1edbcdcc72d7dbee7b8d985f74f9590a7.
Artifact audit SHA95fc96f43d614ca3a2adbef52389050ccc90d14ebfcffc2d1b890d4e016834ad.
Public registry SHA2c3418f4c7676cc67b58831f0789a06e2521d279926151147016dc11147a876d.
All three private scripts pass Ruff; whitespace and public-link/hash checks pass.
No GPU performance claim or final-panel reuse. DINO10k, complete numerical/
native review and PROMPT.md's quality/speed requirements remain pending.
