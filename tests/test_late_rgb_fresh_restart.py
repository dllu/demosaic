import json

import pytest
from audit_late_rgb_fresh_restart import metric_prefix


def log(steps):
    return "\n".join(json.dumps({"event": "train", "step": step}) for step in steps)


def test_prefix_uses_actual_step_boundary_without_stdout_start_events():
    text = log(range(1, 17))
    prefix = metric_prefix(text)
    assert [json.loads(x)["step"] for x in prefix.splitlines()] == list(range(1, 9))


@pytest.mark.parametrize(
    "steps",
    [
        range(1, 9),
        [1, 2, 3, 4, 5, 6, 8, 9],
        [1, 2, 3, 4, 5, 6, 7, 8, 10],
        [1, 2, 3, 4, 5, 6, 7, 8, 8, 9],
    ],
)
def test_missing_duplicate_or_wrong_resume_boundary_is_rejected(steps):
    with pytest.raises(AssertionError):
        metric_prefix(log(steps))
