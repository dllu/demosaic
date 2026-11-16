"""Isolate per-harmonic support and a piecewise-affine background competitor."""

import argparse
from dataclasses import replace
from pathlib import Path

from study_local_wave_shapes import REPO, prepare

from demosaic.experiments.artifacts import reference
from demosaic.local_validated_waves import LocalWaveConfig


def prepare_individual(root):
    previous = REPO / ".cache/experiments/local-wave-shapes-pilot-v1"
    config = replace(LocalWaveConfig(), harmonics=3, support_unit="harmonic")
    return prepare(
        root,
        control_root=previous / "harmonics",
        configurations={
            "individual": config,
            "background": replace(config, background="piecewise_affine"),
        },
        comparison_sources={
            name: reference(previous / arm / "plan.json")
            for name, arm in [("H1", "matching"), ("H3 group", "harmonics")]
        },
        study_question="Separate per-harmonic validation from richer competing background. Reuse H1/cardinality and H3/group/step controls without new predictions. First new arm retains identical H3 discovery/fits but validates each harmonic against a null retaining all other components; each harmonic must match folds within1.5 of its actual native frequency bins. Second arm additionally fits separate affine slopes on each side of the A-only discovered edge and reselects/refines waves after that nuisance. Same original24 development cases, parents/RAW/splits/noise/ROIs/protected scenes/JPEGs, primaryt2 and sweep0/2/4. No GT-based choices. Close both new arms before new scoring. A positive empirical support score is not a calibrated fidelity guarantee.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(prepare_individual(args.root.resolve()))
