"""Build a separate paired training dataset from an exact registered review."""

import argparse
import json
from pathlib import Path

from demosaic.paired_admission import extend_paired_training

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("base_manifest", type=Path)
parser.add_argument("admission", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
print(
    json.dumps(extend_paired_training(args.base_manifest, args.admission, args.output)), flush=True
)
