"""Score donor-supported phase harmonics with calibration by held-out geometry."""

import argparse
import os
from pathlib import Path

from report_oriented_raw_support import report

LABELS = {
    "square": "Full phase fit",
    "fundamental": "Fundamental only",
    "donor-basis": "Donor harmonics",
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve(), labels=LABELS, driver=__file__)
