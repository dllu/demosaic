"""Reuse saved-array and native-board audits with the native-data criteria."""

import argparse
from pathlib import Path

from close_bank_detachment_review import main as close
from score_native_data_eligibility import main as criteria
from train_directional_interval_trial import read, ref

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    plan = parser.parse_args().plan
    assert ref(__file__) == read(plan)["worker"]
    close(plan, numerical_criteria=criteria)
