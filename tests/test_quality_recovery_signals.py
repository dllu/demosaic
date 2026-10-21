"""Actual owned process-group pause/resume; no model, training or CUDA mock."""

import os
import signal
import subprocess
import sys
import time

import psutil
import pytest
from recover_v43_quality_trial import signal_owned_group, stop_owned_child


def wait_for(predicate):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Owned CPU proof did not reach the expected state")


@pytest.mark.skipif(os.name != "posix", reason="The GB10 controller uses POSIX process groups")
def test_pause_resume_preserves_owned_parent_and_child_and_rejects_wrong_cookie(tmp_path):
    script = tmp_path / "counter.py"
    script.write_text(
        "import subprocess,sys,time\n"
        "from pathlib import Path\n"
        "root=Path(sys.argv[1]); leaf=len(sys.argv)>2\n"
        "if not leaf:\n"
        " child=subprocess.Popen([sys.executable,__file__,str(root),'leaf'])\n"
        " (root/'leaf-pid').write_text(str(child.pid))\n"
        "name='leaf' if leaf else 'parent'; counter=0\n"
        "while True:\n"
        " counter+=1; temporary=root/(name+'.tmp')\n"
        " temporary.write_text(str(counter)); temporary.replace(root/name)\n"
        " time.sleep(0.01)\n"
    )
    with (tmp_path / "worker.log").open("wb") as log:
        process = subprocess.Popen(
            [sys.executable, str(script), str(tmp_path)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1"),
        )
    owner = {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}
    try:
        wait_for(lambda: all((tmp_path / n).exists() for n in ("parent", "leaf", "leaf-pid")))
        leaf = int((tmp_path / "leaf-pid").read_text())
        assert os.getpgid(leaf) == process.pid
        with pytest.raises(AssertionError):
            signal_owned_group({**owner, "created": owner["created"] + 1}, signal.SIGSTOP)

        def counters():
            return tuple(int((tmp_path / n).read_text()) for n in ("parent", "leaf"))

        running = counters()
        wait_for(lambda: all(b > a for a, b in zip(running, counters(), strict=True)))
        signal_owned_group(owner, signal.SIGSTOP)
        wait_for(
            lambda: all(
                psutil.Process(p).status() == psutil.STATUS_STOPPED for p in (process.pid, leaf)
            )
        )
        stopped = counters()
        time.sleep(0.1)
        assert counters() == stopped and process.poll() is None
        assert psutil.Process(process.pid).create_time() == owner["created"]
        signal_owned_group(owner, signal.SIGCONT)
        wait_for(lambda: all(b > a for a, b in zip(stopped, counters(), strict=True)))
        assert process.pid == owner["pid"] and process.poll() is None
        # A resource-wait timeout must also clean up a suspended process group.
        signal_owned_group(owner, signal.SIGSTOP)
        wait_for(lambda: psutil.Process(process.pid).status() == psutil.STATUS_STOPPED)
        stop_owned_child(process, owner)
        assert process.returncode == -signal.SIGTERM
    finally:
        if process.poll() is None:
            signal_owned_group(owner, signal.SIGKILL)
        process.wait(timeout=5)
