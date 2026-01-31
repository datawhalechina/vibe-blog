#!/bin/bash

# ============================================================
# Vibe Blog 本地一键启动脚本
# 功能：同时启动前后端，自动检测并释放占用端口
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 端口配置
BACKEND_PORT=5001
FRONTEND_PORT=5173

# 项目路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOG_DIR="$PROJECT_ROOT/logs"

# 时间戳（精确到秒）
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🚀 Vibe Blog 本地启动脚本${NC}"
echo -e "${BLUE}============================================================${NC}"

# 函数：检查并释放端口
kill_port() {
    local port=$1
    local pids=$(lsof -ti :$port 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}⚠️  端口 $port 被占用，正在释放...${NC}"
        for pid in $pids; do
            echo -e "   杀死进程 PID: $pid"
            kill -9 $pid 2>/dev/null || true
        done
        sleep 1
        echo -e "${GREEN}✅ 端口 $port 已释放${NC}"
    else
        echo -e "${GREEN}✅ 端口 $port 可用${NC}"
    fi
}

# 函数：等待服务启动
wait_for_service() {
    local port=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    echo -e "${YELLOW}⏳ 等待 $name 启动...${NC}"
    while [ $attempt -lt $max_attempts ]; do
        if lsof -ti :$port >/dev/null 2>&1; then
            echo -e "${GREEN}✅ $name 已启动 (端口 $port)${NC}"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $name 启动超时${NC}"
    return 1
}

# 函数：清理后台进程
cleanup() {
    echo -e "\n${YELLOW}🛑 正在停止服务...${NC}"
    
    # 停止后端
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
        echo -e "   后端已停止 (PID: $BACKEND_PID)"
    fi
    
    # 停止前端
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
        echo -e "   前端已停止 (PID: $FRONTEND_PID)"
    fi
    
    echo -e "${GREEN}✅ 所有服务已停止${NC}"
    exit 0
}

# 函数：清理旧日志文件，只保留最近 N 条
cleanup_old_logs() {
    local prefix=$1
    local keep_count=$2
    
    # 获取匹配的日志文件数量
    local log_count=$(ls -1 "$LOG_DIR"/${prefix}_*.log 2>/dev/null | wc -l)
    
    if [ "$log_count" -gt "$keep_count" ]; then
        # 删除最旧的日志文件，只保留最近 keep_count 条
        ls -1t "$LOG_DIR"/${prefix}_*.log | tail -n +$((keep_count + 1)) | xargs rm -f
        local deleted=$((log_count - keep_count))
        echo -e "   清理了 $deleted 条旧的 ${prefix} 日志"
    fi
}

# 捕获 Ctrl+C
trap cleanup SIGINT SIGTERM

# ============================================================
# 主流程
# ============================================================

echo -e "\n${BLUE}📍 项目路径: $PROJECT_ROOT${NC}"

# 1. 检查并释放端口
echo -e "\n${BLUE}[1/4] 检查端口占用${NC}"
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# 2. 检查环境
echo -e "\n${BLUE}[2/4] 检查环境${NC}"

# 检查后端 .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${RED}❌ 后端 .env 文件不存在${NC}"
    echo -e "   请复制 .env.example 并配置: cp $BACKEND_DIR/.env.example $BACKEND_DIR/.env"
    exit 1
fi
echo -e "${GREEN}✅ 后端 .env 已配置${NC}"

# 检查 node_modules
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}⚠️  前端依赖未安装，正在安装...${NC}"
    cd "$FRONTEND_DIR" && npm install
fi
echo -e "${GREEN}✅ 前端依赖已安装${NC}"

# 3. 创建日志目录并清理旧日志
echo -e "\n${BLUE}[3/5] 创建日志目录${NC}"
mkdir -p "$LOG_DIR"
echo -e "${GREEN}✅ 日志目录: $LOG_DIR${NC}"

# 清理旧日志，前后端各保留最近 8 条
cleanup_old_logs "backend" 8
cleanup_old_logs "frontend" 8

# 4. 启动后端
echo -e "\n${BLUE}[4/5] 启动后端${NC}"
cd "$BACKEND_DIR"
BACKEND_LOG="$LOG_DIR/backend_${TIMESTAMP}.log"
python app.py > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
echo -e "   后端 PID: $BACKEND_PID"
echo -e "   日志: $BACKEND_LOG"

# 5. 启动前端
echo -e "\n${BLUE}[5/5] 启动前端${NC}"
cd "$FRONTEND_DIR"
FRONTEND_LOG="$LOG_DIR/frontend_${TIMESTAMP}.log"
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
echo -e "   前端 PID: $FRONTEND_PID"
echo -e "   日志: $FRONTEND_LOG"

# 等待服务启动
echo ""
wait_for_service $BACKEND_PORT "后端"
wait_for_service $FRONTEND_PORT "前端"

# 完成
echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}🎉 Vibe Blog 启动成功！${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e ""
echo -e "   ${BLUE}前端地址:${NC} http://localhost:$FRONTEND_PORT"
echo -e "   ${BLUE}后端地址:${NC} http://localhost:$BACKEND_PORT"
echo -e ""
echo -e "   ${YELLOW}按 Ctrl+C 停止所有服务${NC}"
echo -e ""

# 保持脚本运行，等待用户中断
wait
