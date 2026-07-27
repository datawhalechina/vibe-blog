import os
import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _css_rule(source: str, selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]*)\}}", source)
    assert match is not None, f"missing CSS rule: {selector}"
    return match.group("body")


def test_e2e_runner_preserves_pytest_exit_status_through_tee():
    runner = _read("tests/e2e/tools/run_e2e.sh")

    assert "set -o pipefail" in runner
    assert 'set +e\nif [ "$SMOKE" = true ]' in runner
    assert 'fi\nset -e\n\necho ""' in runner
    assert 'mkdir -p "$SCREENSHOT_DIR" "$LOG_DIR"' in runner
    assert 'ls -1 "$SCREENSHOT_DIR"/*.png' not in runner


def test_e2e_runner_registers_cleanup_for_all_exit_paths():
    runner = _read("tests/e2e/tools/run_e2e.sh")

    assert "trap cleanup_services EXIT" in runner
    assert "trap 'exit 130' INT" in runner
    assert "trap 'exit 143' TERM" in runner


def test_e2e_runner_returns_the_failing_pytest_status(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_uv = fake_bin / "uv"
    fake_uv.write_text(
        """#!/bin/sh
case " $* " in
  *" pytest "*)
    echo "fake pytest failure"
    exit 7
    ;;
  *)
    exit 0
    ;;
esac
""",
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)

    fake_lsof = fake_bin / "lsof"
    fake_lsof.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_lsof.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["VIBE_RUNTIME_DIR"] = str(tmp_path / "runtime")
    result = subprocess.run(
        ["bash", "tests/e2e/tools/run_e2e.sh", "--test-only", "--smoke"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 7
    assert "fake pytest failure" in output
    assert "E2E 测试有失败 (exit code: 7)" in output


def test_ui_cases_use_the_shared_tiptap_input_contract():
    responsive = _read("tests/e2e/test_tc11_responsive.py")
    error_cases = _read("tests/e2e/test_tc12_error.py")

    for source in (responsive, error_cases):
        assert "textarea.code-input-textarea" not in source
        assert "INPUT_SELECTORS" in source


def test_quality_dialog_case_selects_the_named_action():
    quality_cases = _read("tests/e2e/test_tc14_quality_eval.py")

    assert ".card-toolbar button:has(svg)" not in quality_cases
    assert 'get_by_role("button", name="质量评估")' in quality_cases


def test_history_click_target_is_stationary():
    home = _read("frontend/src/views/Home.vue")
    click_target = _css_rule(home, ".scroll-hint")
    animated_arrow = _css_rule(home, ".scroll-hint-arrow")

    assert "animation:" not in click_target
    assert "z-index:" in click_target
    assert "animation:" in animated_arrow
