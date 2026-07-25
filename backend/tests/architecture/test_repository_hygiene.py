import subprocess
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_backend_runtime_outputs_are_not_tracked():
    result = subprocess.run(
        ["git", "ls-files", "--", "backend/outputs"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked_outputs = [line for line in result.stdout.splitlines() if line]

    assert tracked_outputs == []
