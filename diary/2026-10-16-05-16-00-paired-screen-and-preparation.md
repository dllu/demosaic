# Actual paired-data screening and alignment pilot

The additional59-scene/231-file acquisition is live in frozene2db058, one worker,
512GiB reserve. Added a separate screen for both clean references: cached42
protected RAW/GFX references and all4558 Commons val/test images;56 views on
both sides with the same conservative dHash/correlation policy used for incoming
Commons. Flags/unknown cameras/flat references hold a scene, and duplicate or
unsafe identities cannot collide in the outcome ledger. Existing train32 and
all active model data remain fixed.

Actual Bark/Blombukett RAWs decode as Canon EOS6D. Two scenes pass the pilot
screen and four noisy pairs register, yielding36 verified512px crops. Native
data pairs and resized content previews are published as data review only;
the AHD reference is independent and not exact RGB GT. Apertures match within
each series but shutter times differ substantially, so reference motion/fine
sharpness must still be reviewed. No training admission follows from the pilot.
Pilot archives retain their exact execution versions; post-test full review
will use a frozen checkout.

Added per-scene quarantine preparation with atomic outcomes, failure isolation,
verified NPZ paths/hashes/dimensions/dtypes/finiteness and measured-reference
mask consistency. Aggregate paths preserve per-scene provenance and keep the
quarantine split. Eleven targeted screen/preparation tests pass; original/new
acquisition tests separately pass16. No current enlarged full-suite claim.

Matched no-context/S/B continuation and ADC-policy queue stay live. No-context
has completed3000; S is continuing, B awaits its turn. The goal is incomplete:
broader real-image superiority, mature context attribution, protected-final
quality and the10-second target still require evidence.
