"""
博客记忆更新 Prompt 模板

借鉴 DeerFlow MEMORY_UPDATE_PROMPT，适配 vibe-blog 博客写作场景。
将 DeerFlow 6 维上下文映射到 writingProfile + topicHistory + qualityPreferences。
"""


def format_conversation(messages: list[dict]) -> str:
    """将消息列表格式化为对话文本"""
    if not messages:
        return ""
    lines = []
    role_map = {"user": "用户", "assistant": "助手", "system": "系统"}
    for msg in messages:
        role = role_map.get(msg.get("role", ""), msg.get("role", ""))
        content = msg.get("content", "")
        if content:
            lines.append(f"[{role}]: {content}")
    return "\n".join(lines)


BLOG_MEMORY_UPDATE_PROMPT = """你是一个博客写作记忆分析器。分析以下对话，提取用户的写作偏好、主题兴趣和关键事实。

## 当前记忆状态
{current_memory}

## 最近对话
{conversation}

## 输出要求

分析对话内容，输出 JSON（不要包裹在 markdown 代码块中）：

{{
  "writingProfile": {{
    "preferredStyle": {{"summary": "写作风格偏好摘要", "shouldUpdate": true/false}},
    "preferredLength": {{"summary": "文章长度偏好", "shouldUpdate": true/false}},
    "preferredAudience": {{"summary": "目标受众描述", "shouldUpdate": true/false}},
    "preferredImageStyle": {{"summary": "配图风格偏好", "shouldUpdate": true/false}}
  }},
  "topicHistory": {{
    "recentTopics": {{"summary": "近期关注的主题列表", "shouldUpdate": true/false}},
    "topicClusters": {{"summary": "核心领域聚类", "shouldUpdate": true/false}},
    "avoidTopics": {{"summary": "已写过/要避免的主题", "shouldUpdate": true/false}}
  }},
  "qualityPreferences": {{
    "revisionPatterns": {{"summary": "修订偏好模式", "shouldUpdate": true/false}},
    "feedbackHistory": {{"summary": "反馈历史摘要", "shouldUpdate": true/false}}
  }},
  "newFacts": [
    {{
      "content": "事实描述",
      "category": "preference|knowledge|context|behavior|goal",
      "confidence": 0.0-1.0
    }}
  ],
  "factsToRemove": ["fact_id_1"]
}}

## 规则
1. 只在对话中有明确信号时设置 shouldUpdate=true
2. 事实分 5 类：preference（偏好）、knowledge（知识）、context（背景）、behavior（行为）、goal（目标）
3. 置信度评分：明确陈述 0.9+，强暗示 0.7-0.9，弱推测 0.4-0.7
4. 保留对话原始语言（中文对话用中文摘要）
5. summary 应简洁（1-3 句），合并而非替换已有信息
6. factsToRemove 仅在对话明确否定已有事实时使用"""
