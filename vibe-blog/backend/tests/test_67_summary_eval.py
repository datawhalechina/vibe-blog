#!/usr/bin/env python3
"""
[需求点 67] SummaryGenerator Agent — LLM-as-Judge 特性验收

验证逻辑：
  1. 准备一篇完整的技术博客文章
  2. 调用 SummaryGeneratorAgent
  3. 用 LLM Judge 评估生成的摘要质量

检查项：
  S1 TL;DR 质量    — 2-3 句话，包含主题+收获+受众
  S2 SEO 关键词数量 — 10-15 个关键词
  S3 SEO 关键词质量 — 包含核心技术术语（中英文）
  S4 社交摘要质量   — 50-100 字，有吸引力
  S5 Meta 描述质量  — 150 字以内，包含核心关键词
  S6 JSON 格式完整  — 四个字段都存在且非空

通过标准：6 项中至少 4 项 pass

用法：
  cd backend
  python tests/test_67_summary_eval.py
"""

import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "eval_results" / "67_summary"
PASS_THRESHOLD = 4  # 6 项中至少 4 项 pass

# ============================================================
# 测试样本
# ============================================================

SAMPLE_TITLE = "Docker 容器化部署实战：从入门到生产环境最佳实践"

SAMPLE_ARTICLE = """
# Docker 容器化部署实战：从入门到生产环境最佳实践

## 什么是 Docker？
<!-- PLACEHOLDER_REST -->
"""

SAMPLE_ARTICLE_REST = """
Docker 是一个开源的容器化平台，允许开发者将应用及其依赖打包到一个轻量级、可移植的容器中。
与传统虚拟机不同，Docker 容器共享宿主机的操作系统内核，因此启动速度更快、资源占用更少。

Docker 的核心概念包括：
- **镜像（Image）**：只读模板，包含运行应用所需的一切
- **容器（Container）**：镜像的运行实例
- **Dockerfile**：定义镜像构建步骤的文本文件
- **Docker Compose**：多容器应用的编排工具

## Dockerfile 最佳实践

编写高效的 Dockerfile 是容器化的关键。以下是几个重要原则：

### 多阶段构建

多阶段构建可以显著减小最终镜像的体积。例如，一个 Go 应用的 Dockerfile：

```dockerfile
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN go build -o main .

FROM alpine:3.18
COPY --from=builder /app/main /main
CMD ["/main"]
```

### 层缓存优化

Docker 按层缓存，将不常变化的指令放在前面可以提高构建速度：

```dockerfile
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o main .
```

## Docker Compose 编排

对于多服务应用，Docker Compose 提供了声明式的编排方式：

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8080:8080"
    depends_on:
      - db
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
```

## 生产环境部署

在生产环境中，需要考虑以下方面：

1. **健康检查**：配置 HEALTHCHECK 指令确保容器正常运行
2. **资源限制**：使用 --memory 和 --cpus 限制容器资源
3. **日志管理**：配置日志驱动，避免日志文件无限增长
4. **安全加固**：使用非 root 用户运行容器，扫描镜像漏洞

## 总结

Docker 容器化技术已成为现代软件开发和部署的标准实践。掌握 Dockerfile 编写、
Docker Compose 编排和生产环境最佳实践，能够帮助团队实现更高效、更可靠的应用交付。
"""

SAMPLE_LEARNING_OBJECTIVES = [
    "理解 Docker 核心概念（镜像、容器、Dockerfile）",
    "掌握 Dockerfile 最佳实践（多阶段构建、层缓存）",
    "学会使用 Docker Compose 编排多服务应用",
    "了解生产环境部署的安全和运维要点",
]

# ============================================================
# Judge Prompt
# ============================================================

JUDGE_PROMPT = """你是一个严格的 Agent 输出质量评估专家。

你将看到一个摘要生成 Agent 的输入和输出，请评估 Agent 是否正确完成了摘要生成任务。

## 文章标题
{title}

## 文章内容（摘要）
{article_excerpt}

## 学习目标
{learning_objectives}

## Agent 输出
{agent_output}

---

请逐项检查以下维度：

### S1 TL;DR 质量
TL;DR 应为 2-3 句话，包含：文章讲什么 + 读完能学到什么 + 适合谁。
不应以"本文将介绍"开头。
- pass: 满足上述要求
- fail: 不满足

### S2 SEO 关键词数量
seo_keywords 应包含 10-15 个关键词。
- pass: 数量在 8-18 范围内（允许小幅偏差）
- fail: 数量不在范围内

### S3 SEO 关键词质量
关键词应包含核心技术术语，中英文都有（如 Docker、容器化、Dockerfile 等）。
- pass: 包含至少 3 个相关技术术语
- fail: 关键词不相关或缺少核心术语

### S4 社交摘要质量
social_summary 应为 50-100 字，有吸引力，适合社交媒体分享。
- pass: 长度合适且有吸引力
- fail: 长度不合适或缺乏吸引力

### S5 Meta 描述质量
meta_description 应在 150 字以内，包含核心关键词，简洁准确。
- pass: 长度合适且包含关键词
- fail: 过长或缺少关键词

### S6 JSON 格式完整
四个字段（tldr, seo_keywords, social_summary, meta_description）都应存在且非空。
- pass: 四个字段都存在且非空
- fail: 有字段缺失或为空

---

请严格按以下 JSON 格式输出（不要输出其他内容）。每个 reason 限 20 字以内：

```json
{{
  "checks": {{
    "S1_tldr_quality": {{"result": "pass", "reason": "..."}},
    "S2_seo_count": {{"result": "pass", "reason": "..."}},
    "S3_seo_quality": {{"result": "pass", "reason": "..."}},
    "S4_social_summary": {{"result": "pass", "reason": "..."}},
    "S5_meta_description": {{"result": "pass", "reason": "..."}},
    "S6_json_complete": {{"result": "pass", "reason": "..."}}
  }},
  "pass_count": 0,
  "total": 6,
  "verdict": "PASS 或 FAIL",
  "summary": "一句话总结"
}}
```
"""

CHECK_NAMES = {
    "S1_tldr_quality": "S1 TL;DR 质量",
    "S2_seo_count": "S2 SEO 关键词数量",
    "S3_seo_quality": "S3 SEO 关键词质量",
    "S4_social_summary": "S4 社交摘要质量",
    "S5_meta_description": "S5 Meta 描述质量",
    "S6_json_complete": "S6 JSON 格式完整",
}

# ============================================================
# 工具函数
# ============================================================

def get_llm_client():
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.llm_service import get_llm_service, init_llm_service

    llm = get_llm_service()
    if llm is None:
        from config import get_config
        cfg = get_config()
        llm = init_llm_service({
            'AI_PROVIDER_FORMAT': cfg.AI_PROVIDER_FORMAT,
            'OPENAI_API_KEY': cfg.OPENAI_API_KEY,
            'OPENAI_API_BASE': cfg.OPENAI_API_BASE,
            'GOOGLE_API_KEY': getattr(cfg, 'GOOGLE_API_KEY', ''),
            'TEXT_MODEL': cfg.TEXT_MODEL,
        })
    return llm


def _extract_json(text: str) -> dict:
    text = text.strip()
    if '```json' in text:
        start = text.find('```json') + 7
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    elif '```' in text:
        start = text.find('```') + 3
        end = text.find('```', start)
        if end != -1:
            text = text[start:end].strip()
        else:
            text = text[start:].strip()
    return json.loads(text, strict=False)


def run_summary_generator(title, article, learning_objectives, llm_client):
    from services.blog_generator.agents.summary_generator import SummaryGeneratorAgent
    agent = SummaryGeneratorAgent(llm_client)
    logger.info("[SummaryGenerator] 开始生成...")
    start = time.time()
    result = agent.generate(title, article, learning_objectives)
    elapsed = time.time() - start
    logger.info(f"[SummaryGenerator] 完成 ({elapsed:.1f}s)")
    return result, elapsed


def call_judge(title, article_excerpt, learning_objectives, agent_output, llm_client):
    prompt = JUDGE_PROMPT.format(
        title=title,
        article_excerpt=article_excerpt[:2000],
        learning_objectives="\n".join(f"- {obj}" for obj in learning_objectives),
        agent_output=json.dumps(agent_output, ensure_ascii=False, indent=2),
    )
    logger.info("  [Judge] 评估 SummaryGenerator...")
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return _extract_json(response)


def print_report(check_keys, check_names, eval_result, elapsed):
    checks = eval_result.get("checks", {})
    pass_count = sum(1 for k in check_keys if checks.get(k, {}).get("result") == "pass")

    print(f"\n{'=' * 60}")
    print(f"  SummaryGenerator Agent 验收报告 (耗时 {elapsed:.1f}s)")
    print(f"{'=' * 60}")

    for key in check_keys:
        check = checks.get(key, {})
        result = check.get("result", "unknown")
        icon = "PASS" if result == "pass" else "FAIL"
        print(f"  [{icon}] {check_names[key]}: {check.get('reason', 'N/A')}")

    print(f"\n  判定: {pass_count}/{len(check_keys)} 项通过")
    print(f"{'=' * 60}")
    return pass_count


def main():
    print("=" * 60)
    print("  67. SummaryGenerator Agent — LLM-as-Judge 特性验收")
    print("=" * 60)

    llm_client = get_llm_client()

    full_article = SAMPLE_ARTICLE.replace("<!-- PLACEHOLDER_REST -->", SAMPLE_ARTICLE_REST)

    # --- 运行 SummaryGenerator ---
    result, elapsed = run_summary_generator(
        SAMPLE_TITLE, full_article, SAMPLE_LEARNING_OBJECTIVES, llm_client
    )

    # --- 打印 Agent 原始输出 ---
    print(f"\n--- SummaryGenerator Agent 原始输出 ---")
    print(f"  tldr: {result.get('tldr', 'N/A')[:100]}...")
    print(f"  seo_keywords: {result.get('seo_keywords', [])}")
    print(f"  social_summary: {result.get('social_summary', 'N/A')[:100]}...")
    print(f"  meta_description: {result.get('meta_description', 'N/A')[:100]}...")

    # --- Judge 评估 ---
    eval_result = call_judge(
        SAMPLE_TITLE, full_article, SAMPLE_LEARNING_OBJECTIVES, result, llm_client
    )
    check_keys = list(CHECK_NAMES.keys())
    pass_count = print_report(check_keys, CHECK_NAMES, eval_result, elapsed)

    # --- 总结 ---
    print(f"\n{'=' * 60}")
    verdict = "PASS" if pass_count >= PASS_THRESHOLD else "FAIL"
    print(f"  总体判定: {verdict} ({pass_count}/{len(check_keys)} 项通过, 阈值 {PASS_THRESHOLD})")
    print(f"{'=' * 60}")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    eval_data = {
        "feature": "67-summary-generator",
        "agent_output": result,
        "judge_eval": eval_result,
        "pass_count": pass_count,
        "total": len(check_keys),
        "verdict": verdict,
        "elapsed": elapsed,
        "timestamp": datetime.now().isoformat(),
    }
    result_file.write_text(json.dumps(eval_data, ensure_ascii=False, indent=2))
    logger.info(f"  评估结果已保存: {result_file}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    main()
