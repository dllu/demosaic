"""Build a separate private native dataset from a pinned, reviewed admission."""

import argparse
import json
from pathlib import Path

from demosaic.personal_admission import extend_personal_targets

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = extend_personal_targets(args.base, args.admission, args.output)
    print(
        json.dumps(
            {
                "manifest": str(args.output / "manifest.json"),
                "captures": len(result["rows"]),
                "groups": len({r["scene"] for r in result["rows"]}),
            }
        )
    )
