"""Reuse saved-array/native-board audits with the fixed late RGB criteria."""

import argparse
from pathlib import Path

from close_bank_detachment_review import main as close
from score_late_rgb_eligibility import main as criteria
from train_directional_bank_trial import read, ref

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    a = p.parse_args()
    assert ref(__file__) == read(a.plan)["worker"]
    close(a.plan, numerical_criteria=criteria)
