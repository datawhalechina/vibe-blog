#!/usr/bin/env python3
"""
E2E 日志分析器 — vibe-blog-browser-test 日志监控子代理的核心脚本

数据源：
  1. logs/blog_tasks/{task_id}.json  — 结构化任务日志（agent 步骤、token、耗时）
  2. logs/app.log                    — 后端应用日志（最近 N 行）
  3. backend/outputs/e2e_screenshots/ — 浏览器控制台日志 JSON + 截图清单
  4. logs/e2e_result_*.log           — pytest 输出

输出：
  stdout JSON 格式的分析报告，供主代理解析。

用法：
  python scripts/analyze_e2e_logs.py                          # 分析最近一次测试
  python scripts/analyze_e2e_logs.py --task-id <id>           # 分析指定任务
  python scripts/analyze_e2e_logs.py --since 5m               # 分析最近 5 分钟的日志
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
LOGS_DIR = PROJECT_ROOT / "logs"
TASK_LOGS_DIR = LOGS_DIR / "blog_tasks"
APP_LOG = LOGS_DIR / "app.log"
SCREENSHOT_DIR = BACKEND_DIR / "outputs" / "e2e_screenshots"


def parse_args():
    p = argparse.ArgumentParser(description="E2E 日志分析器")
    p.add_argument("--task-id", help="指定分析的 task_id")
    p.add_argument("--since", default="10m", help="分析最近 N 分钟的日志 (如 5m, 1h)")
    p.add_argument("--output", default="-", help="输出文件路径，- 为 stdout")
    return p.parse_args()


def parse_duration(s: str) -> timedelta:
    """解析 '5m', '1h', '30s' 格式"""
    m = re.match(r"(\d+)([smh])", s)
    if not m:
        return timedelta(minutes=10)
    val, unit = int(m.group(1)), m.group(2)
    if unit == "s":
        return timedelta(seconds=val)
    if unit == "h":
        return timedelta(hours=val)
    return timedelta(minutes=val)


# ═══════════════════════════════════════════════════════════════
# 数据源 1: 结构化任务日志
# ═══════════════════════════════════════════════════════════════

def analyze_task_log(task_id: str = None) -> dict:
    """分析 blog_tasks/ 下的任务日志"""
    result = {"found": False, "task_id": None, "summary": {}, "issues": []}

    if not TASK_LOGS_DIR.exists():
        result["issues"].append("blog_tasks 目录不存在")
        return result

    # 找到目标任务日志
    if task_id:
        candidates = list(TASK_LOGS_DIR.glob(f"*{task_id}*.json"))
    else:
        # 取最新的
        candidates = sorted(TASK_LOGS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)

    if not candidates:
        result["issues"].append("未找到任务日志文件")
        return result

    log_path = candidates[0]
    try:
        with open(log_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        result["issues"].append(f"解析任务日志失败: {e}")
        return result

    result["found"] = True
    result["task_id"] = data.get("task_id")
    result["log_file"] = str(log_path.name)

    # 摘要
    result["summary"] = {
        "topic": data.get("topic"),
        "status": data.get("status"),
        "duration_ms": data.get("total_duration_ms"),
        "total_tokens": data.get("total_tokens"),
        "word_count": data.get("word_count"),
        "final_score": data.get("final_score"),
        "steps_count": len(data.get("steps", [])),
    }

    # 检测异常
    steps = data.get("steps", [])
    for step in steps:
        if step.get("level") == "error":
            result["issues"].append(
                f"[{step.get('agent')}] {step.get('action')}: {step.get('detail', '')[:200]}"
            )
        # 单步超过 60s 的慢操作
        dur = step.get("duration_ms", 0)
        if dur and dur > 60000:
            result["issues"].append(
                f"慢操作: [{step.get('agent')}] {step.get('action')} 耗时 {dur/1000:.1f}s"
            )

    # agent 统计
    result["agent_stats"] = data.get("agent_stats", {})
    result["token_summary"] = data.get("token_summary", {})

    return result


# ═══════════════════════════════════════════════════════════════
# 数据源 2: 后端应用日志（最近 N 行）
# ═══════════════════════════════════════════════════════════════

def analyze_app_log(since: timedelta, task_id: str = None) -> dict:
    """扫描 app.log 中的错误和警告"""
    result = {"errors": [], "warnings": [], "lines_scanned": 0}

    if not APP_LOG.exists():
        return result

    cutoff = datetime.now() - since
    error_pattern = re.compile(r"(ERROR|CRITICAL)")
    warn_pattern = re.compile(r"WARNING")
    ts_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")

    try:
        with open(APP_LOG, encoding="utf-8", errors="replace") as f:
            # 从尾部读取（大文件优化）
            f.seek(0, 2)
            size = f.tell()
            read_size = min(size, 2 * 1024 * 1024)  # 最多读 2MB
            f.seek(max(0, size - read_size))
            lines = f.readlines()
    except Exception:
        return result

    for line in lines:
        result["lines_scanned"] += 1

        # 时间过滤
        ts_match = ts_pattern.match(line)
        if ts_match:
            try:
                line_time = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S")
                if line_time < cutoff:
                    continue
            except ValueError:
                pass

        # task_id 过滤
        if task_id and task_id not in line:
            continue

        stripped = line.strip()
        if error_pattern.search(stripped):
            result["errors"].append(stripped[:300])
        elif warn_pattern.search(stripped):
            result["warnings"].append(stripped[:300])

    # 限制数量
    result["errors"] = result["errors"][-20:]
    result["warnings"] = result["warnings"][-10:]
    return result


# ═══════════════════════════════════════════════════════════════
# 数据源 3: 浏览器控制台日志 + 截图清单
# ═══════════════════════════════════════════════════════════════

def analyze_browser_artifacts() -> dict:
    """分析 e2e_screenshots/ 下的控制台日志和截图"""
    result = {"console_errors": [], "screenshots": [], "console_files": []}

    if not SCREENSHOT_DIR.exists():
        return result

    # 截图清单
    pngs = sorted(SCREENSHOT_DIR.glob("*.png"), key=os.path.getmtime, reverse=True)
    result["screenshots"] = [p.name for p in pngs[:30]]

    # 控制台日志 JSON
    jsons = sorted(SCREENSHOT_DIR.glob("*_console_*.json"), key=os.path.getmtime, reverse=True)
    for jf in jsons[:5]:
        result["console_files"].append(jf.name)
        try:
            with open(jf, encoding="utf-8") as f:
                logs = json.load(f)
            for entry in logs:
                if entry.get("type") == "error" and "favicon" not in entry.get("text", "").lower():
                    result["console_errors"].append(entry["text"][:200])
        except Exception:
            pass

    result["console_errors"] = result["console_errors"][-10:]
    return result


# ═══════════════════════════════════════════════════════════════
# 数据源 4: pytest 输出日志
# ═══════════════════════════════════════════════════════════════

def analyze_pytest_output() -> dict:
    """分析最近的 pytest 输出"""
    result = {"passed": 0, "failed": 0, "skipped": 0, "errors": [], "log_file": None}

    log_files = sorted(LOGS_DIR.glob("e2e_result_*.log"), key=os.path.getmtime, reverse=True)
    if not log_files:
        return result

    log_path = log_files[0]
    result["log_file"] = log_path.name

    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return result

    # 解析 pytest summary
    summary_match = re.search(
        r"(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) skipped)?", content
    )
    if summary_match:
        result["passed"] = int(summary_match.group(1) or 0)
        result["failed"] = int(summary_match.group(2) or 0)
        result["skipped"] = int(summary_match.group(3) or 0)

    # 提取 FAILED 测试名
    for m in re.finditer(r"FAILED (.+?)(?:\s|$)", content):
        result["errors"].append(m.group(1)[:200])

    return result


# ═══════════════════════════════════════════════════════════════
# 汇总报告
# ═══════════════════════════════════════════════════════════════

def generate_report(args) -> dict:
    """汇总所有数据源，生成结构化报告"""
    since = parse_duration(args.since)

    report = {
        "generated_at": datetime.now().isoformat(),
        "task_log": analyze_task_log(args.task_id),
        "app_log": analyze_app_log(since, args.task_id),
        "browser": analyze_browser_artifacts(),
        "pytest": analyze_pytest_output(),
        "health": {},
    }

    # 健康度评估
    issues = []
    issues.extend(report["task_log"].get("issues", []))
    issues.extend(report["app_log"].get("errors", []))
    issues.extend(report["browser"].get("console_errors", []))
    issues.extend(report["pytest"].get("errors", []))

    task_status = report["task_log"].get("summary", {}).get("status")
    pytest_failed = report["pytest"].get("failed", 0)

    if not issues and task_status in ("completed", None) and pytest_failed == 0:
        health = "GREEN"
    elif pytest_failed > 0 or task_status == "failed":
        health = "RED"
    else:
        health = "YELLOW"

    report["health"] = {
        "status": health,
        "total_issues": len(issues),
        "top_issues": issues[:5],
    }

    return report


def main():
    args = parse_args()
    report = generate_report(args)

    output = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output == "-":
        print(output)
    else:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"报告已写入: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
