# Phase-aware harmonic patch recovers visible mesh with a localization cost

Recorded: 2026-11-02T13:11:58-08:00 (America/Los_Angeles).

The [phase-aware harmonic patch](../docs/phase-harmonic-patch.md) is the first visibly stronger extra-mesh result in this sequence. It uses existing input-only phase-compensated green cross spectra, fixedscore>5/coherence>.8/radial.03–.22/max4separatedpeaks, then weighted RAW-minus-parent harmonic fits at physical CFA coordinates, shared green-innovation shrink and Hann localization. All constants were fixed before real/flat/photo checks; no GT/reference enters correction. No new model calls, noise or RAW decoding. Original/private/public operators and receipts preserved.

Both finegreen windows/priors now show a clearer soft lattice, still much weaker than independentISO100/AHD/JPEG. Main sky/building/foliage retain parentvalues; larger fence changes slightly. On the strongest of4 procedural recipes, mean gain.00397→.29807 and spatialRMS23.92494→19.08899DN16 across4CFAs. Across16noisy-present cases, gain.00095→.07447 and spatialRMS12.43013→11.22114. The other3recipes and16noisyabsent cases remain unchanged.96retainedphoto predictions and48exactflat fields retain parentpixelvalues.

The900exactempty pixels inside the strong texturedcase worsen: RMS3.99–6.56→5.30–7.84DN16. This exposes periodic overextension and prevents broad flatsafety/default-use claims. Coherence/shrink scores are uncalibrated, including inverse weighted-Gram proxy; no false-discovery guarantee. Native256CPU savedpatch implementation only, no fullframe/tile-seam testing. Document as useful experimental option and put stronger mesh comparisons inREADME without hiding this cost. V120 remains general recommendation.

Four-CFA harmonic geometry/uniform/ADC/invalidinput tests:9pass. Public/private parity verifies7,864,320values across40patches. ActualCLI executes one retainedpatch and matches196,608values exactly; outputremainslinearfloat64.16boardsactuallyviewed, including2photo+2procedural exactGTtriplets, bothGFXscenes/priors/JPEGs. Independentdirectmatrix/gamma andoriginalcell checks5,222,400PNGchannels exactly.

Separately, originalV143worker completedall5000updates; v4endpointcollector/primary/faint/flat audits passed andawaitactualnativeviewing. Originaltrainingstatusremains preservedstaleaftercontrollerloss; endpointusesgenuine originalworkerresult. PreliminaryfaintPSNR67.74560dB, tobecombinedwithcompleteendpointnative/flatreview. No checkpoint/network change is made by this harmonicstage.
