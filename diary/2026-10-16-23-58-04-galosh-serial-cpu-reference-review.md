# Recent search-free RAW reference while V67 trains

Previous turn was progress: actual V67 production500 state independently checked
and published/pushed as9a554ae. Revalidated actual V67 trainer and three review
controller PID/creation identities; trainer advanced625→1425 during this turn,
with unchanged recipe/model/source. Routine8-photo validation improves, but full
quality/native review still waits for the declared2000 boundary.

Primary-source follow-up found July2026 GALOSH (arxiv2607.03768), with Apache-2.0
C CPU/OpenCL/Vulkan reference. Pinned official11de0593cc8091933ad76d1d6d873f7dee537f15
in external storage. CPU build fails on unconditional x86 intrinsic headers. An
explicit local AArch64 port guards those includes and two archived SSE helpers
with zero call sites; no canonical processing code changes. Retain upstream
license/notice, source hashes, compiler/flags and binarySHAf2bef9c... in receipts.
Original x86/GPU numerical parity remains unverified; no GPU work launched.

Ran two fixed CPU-noise photos and four original cached GFX512 contexts in blind
and supplied-nominal modes, explicit unit luma/chroma strengths. Inputs clipped
to publisher[0,1] with counts retained, not silently equated with signed neural
preprocessing. Noise profile is nominal and internal stabilized-sigma reestimation
remains. No new noise/RAW decode/target fitting/training/protected-final scores.

First two-thread attempt passes artifact checks but fails exact photo0 repeat:
52185 RAW samples differ, max2.5212765e-5/RMS4.8143006e-7. Preserve its report and
failed-repeat receipt; no widened tolerance. Rerun separately with OpenMP1. The
serial repeat is byte-identical. Both builds reproduce the same executable SHA.
Serial independent layout/clipping/command contract,8 Torch64 PSNR fields
(max5.42e-7dB/declared3e-5) and36 exact native panel rerenders pass. Original
noisy/reference pixels are exact. Actually viewed all12 serial triplets at100%,
plus first12 earlier views. Six unchanged serial PNGs in the human report include
two exact-GT photos and sky/building/foliage/fence non-GT GFX regions.

Grain is greatly reduced but cords, facade/leaf definition and especially fence
contrast are lost; sky remains mottled. No promotion or full/GPU benchmark follows
from this selected reference pilot. It helps bound the local-shrinkage tradeoff,
not the project's quality objective. V43 remains working reference; V67 continues.
Public report docs/galosh-cpu-pilot.md, all source/conditioning/ROI/binary/display
receipts docs/results/galosh-cpu-pilot.json SHA256
e2769cbd65318d2b3bcf354614d773f94f1ddfdad51d1229ba34ffb03591afc8.
New build/probe/audit scripts execute against genuine publisher sources and saved
observations. Ruff, JSON/hash/local-link/whitespace checks pass. No neural source
change or rerun of the already-passing543-test model suite is claimed.
