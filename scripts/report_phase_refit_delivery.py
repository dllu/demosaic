"""Score post-validation RAW refits at fixed thresholds and held-out quiet budgets."""

import argparse
import os
from pathlib import Path

from report_oriented_raw_support import report

LABELS = {
    "square": "Fold-averaged fit",
    "all-site-refit": "All-site refit",
    "weighted-refit": "Weighted refit",
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    report(parser.parse_args().path.resolve(), labels=LABELS, driver=__file__)
