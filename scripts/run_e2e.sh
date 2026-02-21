#!/bin/bash

# ============================================================
# vibe-blog E2E 测试一键运行脚本
#
# 功能：
#   1. 检查/重启前后端服务
#   2. 运行 pytest E2E 测试（真实 LLM 调用）
#   3. 收集截图和日志到 outputs 目录
#
# 用法：
#   bash scripts/run_e2e.sh              # 完整流程（检查服务 + 跑测试）
#   bash scripts/run_e2e.sh --restart    # 强制重启服务后跑测试
#   bash scripts/run_e2e.sh --test-only  # 跳过服务检查，直接跑测试
#   bash scripts/run_e2e.sh --smoke      # 只跑 smoke 测试（TC-01 + TC-02）
#   bash scripts/run_e2e.sh --chain      # 全链路闭环测试（TC-16）
#   bash scripts/run_e2e.sh --headed     # 有头模式（显示浏览器窗口）
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
E2E_DIR="$PROJECT_ROOT/tests/e2e"
SCREENSHOT_DIR="$BACKEND_DIR/outputs/e2e_screenshots"
LOG_DIR="$PROJECT_ROOT/logs"

BACKEND_PORT=5001
FRONTEND_PORT=5173

# 解析参数
RESTART=false
TEST_ONLY=false
SMOKE=false
CHAIN=false
HEADED=false
EXTRA_PYTEST_ARGS=""

for arg in "$@"; do
    case $arg in
        --restart)   RESTART=true ;;
        --test-only) TEST_ONLY=true ;;
        --smoke)     SMOKE=true ;;
        --chain)     CHAIN=true ;;
        --headed)    HEADED=true ;;
        *)           EXTRA_PYTEST_ARGS="$EXTRA_PYTEST_ARGS $arg" ;;
    esac
done

# ── 工具函数 ──

check_port() {
    lsof -ti :$1 >/dev/null 2>&1
}

wait_for_service() {
    local port=$1 name=$2 max=30 attempt=0
    echo -e "${YELLOW}⏳ 等待 $name (端口 $port)...${NC}"
    while [ $attempt -lt $max ]; do
        if check_port $port; then
            echo -e "${GREEN}✅ $name 就绪${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    echo -e "${RED}❌ $name 启动超时${NC}"
    return 1
}

kill_port() {
    local pids=$(lsof -ti :$1 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}停止端口 $1 上的进程...${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# ============================================================
# 主流程
# ============================================================

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  vibe-blog E2E 测试${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "  项目: $PROJECT_ROOT"
echo -e "  模式: $([ "$CHAIN" = true ] && echo "chain" || ([ "$SMOKE" = true ] && echo "smoke" || echo "full"))"
echo -e "  浏览器: $([ "$HEADED" = true ] && echo "有头" || echo "无头")"
echo ""

# ── Step 1: 服务管理 ──

if [ "$TEST_ONLY" = false ]; then
    echo -e "${BLUE}[Step 1] 检查服务状态${NC}"

    if [ "$RESTART" = true ]; then
        echo -e "${YELLOW}强制重启服务...${NC}"
        kill_port $BACKEND_PORT
        kill_port $FRONTEND_PORT
    fi

    NEED_BACKEND=false
    NEED_FRONTEND=false
    STARTED_BACKEND=false
    STARTED_FRONTEND=false

    if ! check_port $BACKEND_PORT; then
        NEED_BACKEND=true
        echo -e "${YELLOW}后端未运行，启动中...${NC}"
        mkdir -p "$LOG_DIR"
        TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
        cd "$BACKEND_DIR" && python app.py > "$LOG_DIR/backend_e2e_${TIMESTAMP}.log" 2>&1 &
        BACKEND_PID=$!
        STARTED_BACKEND=true
    else
        echo -e "${GREEN}✅ 后端已运行${NC}"
    fi

    if ! check_port $FRONTEND_PORT; then
        NEED_FRONTEND=true
        echo -e "${YELLOW}前端未运行，启动中...${NC}"
        mkdir -p "$LOG_DIR"
        TIMESTAMP=${TIMESTAMP:-$(date +"%Y%m%d_%H%M%S")}
        cd "$FRONTEND_DIR" && npm run dev > "$LOG_DIR/frontend_e2e_${TIMESTAMP}.log" 2>&1 &
        FRONTEND_PID=$!
        STARTED_FRONTEND=true
    else
        echo -e "${GREEN}✅ 前端已运行${NC}"
    fi

    # 等待新启动的服务就绪
    if [ "$NEED_BACKEND" = true ]; then
        wait_for_service $BACKEND_PORT "后端" || exit 1
    fi
    if [ "$NEED_FRONTEND" = true ]; then
        wait_for_service $FRONTEND_PORT "前端" || exit 1
    fi
else
    echo -e "${BLUE}[Step 1] 跳过服务检查 (--test-only)${NC}"
    if ! check_port $BACKEND_PORT || ! check_port $FRONTEND_PORT; then
        echo -e "${RED}❌ 服务未运行，请先启动或去掉 --test-only${NC}"
        exit 1
    fi
fi

echo ""

# ── Step 2: 准备测试环境 ──

echo -e "${BLUE}[Step 2] 准备测试环境${NC}"

# 清理旧截图
if [ -d "$SCREENSHOT_DIR" ]; then
    OLD_COUNT=$(ls -1 "$SCREENSHOT_DIR" 2>/dev/null | wc -l)
    if [ "$OLD_COUNT" -gt 0 ]; then
        echo -e "  清理 $OLD_COUNT 个旧截图"
        rm -f "$SCREENSHOT_DIR"/*.png "$SCREENSHOT_DIR"/*.json
    fi
fi
mkdir -p "$SCREENSHOT_DIR"

# 设置环境变量
export RUN_E2E_TESTS=1
if [ "$HEADED" = true ]; then
    export E2E_HEADED=1
    export E2E_SLOW_MO=300
fi

echo -e "${GREEN}✅ 环境就绪${NC}"
echo ""

# ── Step 3: 运行测试 ──

echo -e "${BLUE}[Step 3] 运行 E2E 测试${NC}"

cd "$PROJECT_ROOT"

if [ "$SMOKE" = true ]; then
    echo -e "  运行 smoke 测试 (TC-01 + TC-02)..."
    python -m pytest tests/e2e/test_tc01_home_load.py tests/e2e/test_tc02_blog_gen.py \
        -v --tb=short $EXTRA_PYTEST_ARGS 2>&1 | tee "$LOG_DIR/e2e_result_$(date +%H%M%S).log"
    TEST_EXIT=$?
elif [ "$CHAIN" = true ]; then
    echo -e "  运行全链路闭环测试 (TC-16)..."
    python -m pytest tests/e2e/test_tc16_full_chain.py \
        -v --tb=short $EXTRA_PYTEST_ARGS 2>&1 | tee "$LOG_DIR/e2e_result_$(date +%H%M%S).log"
    TEST_EXIT=$?
else
    echo -e "  运行完整 E2E 测试..."
    python -m pytest tests/e2e/ \
        -v --tb=short $EXTRA_PYTEST_ARGS 2>&1 | tee "$LOG_DIR/e2e_result_$(date +%H%M%S).log"
    TEST_EXIT=$?
fi

echo ""

# ── Step 4: 收集结果 ──

echo -e "${BLUE}[Step 4] 测试结果${NC}"

SCREENSHOT_COUNT=$(ls -1 "$SCREENSHOT_DIR"/*.png 2>/dev/null | wc -l)
LOG_COUNT=$(ls -1 "$SCREENSHOT_DIR"/*.json 2>/dev/null | wc -l)

echo -e "  截图: ${SCREENSHOT_COUNT} 张 → $SCREENSHOT_DIR"
echo -e "  日志: ${LOG_COUNT} 个 → $SCREENSHOT_DIR"

# ── Step 5: 日志分析 ──

echo -e "\n${BLUE}[Step 5] 日志分析${NC}"
ANALYSIS_REPORT="$LOG_DIR/e2e_analysis_$(date +%H%M%S).json"
python "$SCRIPT_DIR/analyze_e2e_logs.py" --since 10m --output "$ANALYSIS_REPORT" 2>/dev/null
if [ -f "$ANALYSIS_REPORT" ]; then
    HEALTH=$(python -c "import json; d=json.load(open('$ANALYSIS_REPORT')); print(d.get('health',{}).get('status','UNKNOWN'))" 2>/dev/null || echo "UNKNOWN")
    ISSUES=$(python -c "import json; d=json.load(open('$ANALYSIS_REPORT')); print(d.get('health',{}).get('total_issues',0))" 2>/dev/null || echo "?")
    if [ "$HEALTH" = "GREEN" ]; then
        echo -e "  ${GREEN}健康度: $HEALTH (问题: $ISSUES)${NC}"
    elif [ "$HEALTH" = "RED" ]; then
        echo -e "  ${RED}健康度: $HEALTH (问题: $ISSUES)${NC}"
    else
        echo -e "  ${YELLOW}健康度: $HEALTH (问题: $ISSUES)${NC}"
    fi
    echo -e "  分析报告: $ANALYSIS_REPORT"
else
    echo -e "  ${YELLOW}日志分析跳过${NC}"
fi

if [ $TEST_EXIT -eq 0 ]; then
    echo -e "\n${GREEN}============================================================${NC}"
    echo -e "${GREEN}  E2E 测试全部通过${NC}"
    echo -e "${GREEN}============================================================${NC}"
else
    echo -e "\n${RED}============================================================${NC}"
    echo -e "${RED}  E2E 测试有失败 (exit code: $TEST_EXIT)${NC}"
    echo -e "${RED}============================================================${NC}"
    echo -e "  查看截图: open $SCREENSHOT_DIR"
    echo -e "  查看日志: ls $LOG_DIR/e2e_result_*.log"
fi

# ── 清理：如果是脚本启动的服务，停掉 ──

if [ "$STARTED_BACKEND" = true ] || [ "$STARTED_FRONTEND" = true ]; then
    echo ""
    echo -e "${YELLOW}清理脚本启动的服务...${NC}"
    [ "$STARTED_BACKEND" = true ] && [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null && echo "  后端已停止"
    [ "$STARTED_FRONTEND" = true ] && [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null && echo "  前端已停止"
fi

exit $TEST_EXIT
