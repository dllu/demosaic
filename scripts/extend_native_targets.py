"""Freeze a separate native RAW extension from a reviewed admission receipt."""

import argparse
import json
from pathlib import Path

from demosaic.raw_admission import extend_native_targets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = extend_native_targets(args.base, args.admission, args.output)
    print(json.dumps({"manifest": str(args.output / "manifest.json"), "captures": len(data["rows"]), "scenes": len({r["scene"] for r in data["rows"]})}))


if __name__ == "__main__":
    main()
