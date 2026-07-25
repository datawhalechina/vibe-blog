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


def test_deprecated_vibe_reviewer_is_removed():
    assert not (REPOSITORY_ROOT / "backend" / "vibe_reviewer").exists()
    assert not (REPOSITORY_ROOT / "frontend" / "src" / "views" / "Reviewer.vue").exists()
    assert not (
        REPOSITORY_ROOT / "backend" / "infrastructure" / "prompts" / "reviewer"
    ).exists()
    assert not (
        REPOSITORY_ROOT / "docs" / "deprecated" / "assets" / "vibe-reviewer"
    ).exists()
    assert not (
        REPOSITORY_ROOT
        / "docs"
        / "plans"
        / "2026-07-21-deprecate-vibe-reviewer-docs.md"
    ).exists()

    env_example = (REPOSITORY_ROOT / "backend" / ".env.example").read_text()
    requirements = (REPOSITORY_ROOT / "backend" / "requirements.txt").read_text()
    pyproject = (REPOSITORY_ROOT / "backend" / "pyproject.toml").read_text()
    assert "REVIEWER_MAX_CHAPTERS" not in env_example
    assert "jieba" not in requirements
    assert "jieba" not in pyproject

    result = subprocess.run(
        [
            "git",
            "grep",
            "-n",
            "-E",
            "vibe_reviewer|REVIEWER_ENABLED|REVIEWER_MAX_CHAPTERS",
            "--",
            "backend",
            "frontend",
            ":!backend/tests/**",
            ":!frontend/__tests__/**",
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1, result.stdout
