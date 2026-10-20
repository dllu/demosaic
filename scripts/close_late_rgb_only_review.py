"""Audit saved arrays and native boards using the V92 historical-reference criteria."""

import argparse
from pathlib import Path

from close_bank_detachment_review import main as close
from score_late_rgb_only_eligibility import main as criteria
from train_directional_bank_trial import read, ref

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    assert ref(__file__) == read(args.plan)["worker"]
    close(args.plan, numerical_criteria=criteria)
