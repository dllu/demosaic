"""Exercise resource control using actual owned CPU workers, without model inference."""

import os
import subprocess
import sys
import time
from contextlib import contextmanager

import psutil
import pytest
from evaluate_v43_quality_trial import monitor_child
from recover_v43_quality_trial import stop_owned_child
from train_directional_bank_trial import ref

pytestmark = pytest.mark.skipif(os.name != "posix", reason="GB10 uses POSIX process groups")


def wait_for(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("Owned CPU worker did not reach the expected state")


@contextmanager
def owned_counter(root):
    script = root / "counter.py"
    script.write_text(
        "import sys,time\n"
        "from pathlib import Path\n"
        "root=Path(sys.argv[1]); counter=0\n"
        "while not (root/'release').exists():\n"
        " counter+=1; temporary=root/'counter.tmp'\n"
        " temporary.write_text(str(counter)); temporary.replace(root/'counter')\n"
        " time.sleep(0.005)\n"
    )
    with (root / "worker.log").open("wb") as log:
        child = subprocess.Popen(
            [sys.executable, str(script), str(root)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1"),
        )
    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    try:
        wait_for(lambda: (root / "counter").exists())
        yield child, owner
    finally:
        stop_owned_child(child, owner)
        child.wait(timeout=5)


def reading(**changes):
    return dict(
        {
            "RAM_available_bytes": 64 * 2**30,
            "root_free_bytes": 65 * 2**30,
            "external_free_bytes": 385 * 2**30,
            "external_is_mount": True,
            "external_device": 1234,
        },
        **changes,
    )


@pytest.mark.parametrize("change_frozen_input", [False, True])
def test_disk_pause_keeps_same_worker_and_checks_inputs_before_resuming(
    tmp_path, change_frozen_input
):
    frozen = tmp_path / "input"
    frozen.write_text("frozen")
    plan = {
        "inputs": [ref(frozen)],
        "frozen_files": {},
        "disk_reserves": {"root_reserve_gib": 64, "external_reserve_gib": 384},
        "external_device": 1234,
        "wait_seconds": 5,
        "stable_seconds": 0.02,
    }
    samples, events, paused_counter = [], [], None
    with owned_counter(tmp_path) as (child, owner):

        def count():
            return int((tmp_path / "counter").read_text())

        def observe():
            if not samples:
                sample = reading(root_free_bytes=63 * 2**30)
            elif len(samples) <= 2:
                # Adequate active RAM alone must not resume a suspended worker.
                sample = reading(RAM_available_bytes=47 * 2**30)
            else:
                sample = reading()
            if paused_counter is not None and len(events) == 1:
                assert psutil.Process(child.pid).status() == psutil.STATUS_STOPPED
                assert count() == paused_counter
            samples.append(sample)
            return sample

        def record(status, **extra):
            nonlocal paused_counter
            events.append(status)
            if status == "paused-V43-evaluation-disk-reserve":
                wait_for(lambda: psutil.Process(child.pid).status() == psutil.STATUS_STOPPED)
                paused_counter = count()
                if change_frozen_input:
                    frozen.write_text("changed during pause")
            else:
                assert status == "running-V43-quality-evaluation"
                assert extra["resumed_same_worker"]
                assert psutil.Process(child.pid).create_time() == owner["created"]
                wait_for(lambda: count() > paused_counter)
                (tmp_path / "release").touch()

        kwargs = {
            "plan": plan,
            "observe": observe,
            "record": record,
            "deadline": time.monotonic() + 5,
            "poll_seconds": 0.005,
        }
        if change_frozen_input:
            with pytest.raises(AssertionError):
                monitor_child(child, owner, **kwargs)
            assert events == ["paused-V43-evaluation-disk-reserve"]
            assert psutil.Process(child.pid).status() == psutil.STATUS_STOPPED
        else:
            monitor_child(child, owner, **kwargs)
            assert child.wait(timeout=5) == 0
            assert events == [
                "paused-V43-evaluation-disk-reserve",
                "running-V43-quality-evaluation",
            ]
        assert len(samples) >= 5


def test_ram_floor_preserves_reading_and_does_not_suspend_worker(tmp_path):
    sample = reading(RAM_available_bytes=23 * 2**30)
    with owned_counter(tmp_path) as (child, owner):
        with pytest.raises(AssertionError) as error:
            monitor_child(
                child,
                owner,
                plan={},
                observe=lambda: sample,
                record=lambda *args, **kwargs: pytest.fail("RAM breach must not pause"),
                deadline=time.monotonic() + 5,
            )
        assert error.value.args == (sample,)
        assert child.poll() is None
        assert psutil.Process(child.pid).status() != psutil.STATUS_STOPPED
