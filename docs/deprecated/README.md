# 已弃用功能清单

本目录记录已经退出主要产品路径、但代码仍可能因兼容或迁移需要暂时保留的功能。根目录 README 仅展示当前维护并推荐使用的能力。

| 功能 | 状态 | 弃用日期 | 删除日期/版本 | 原入口 | 替代方案 |
| --- | --- | --- | --- | --- | --- |
| vibe-reviewer 技术教程质量评估 | 已删除 | 2026-07-21 | 2026-07-26 / 0.1.0 | `/reviewer`、`/api/reviewer/*` | 暂无直接替代；博客生成流程继续使用内部 Reviewer Agent 进行文章质量检查 |

## vibe-reviewer

vibe-reviewer 曾用于克隆 Git 仓库并评估技术教程质量。该独立子产品已于 2026-07-26 从 VibeBlog 删除，包括后端服务、API、配置、前端页面和历史截图；旧前端地址 `/reviewer` 暂时跳转首页。

删除范围：

- 删除 `backend/vibe_reviewer/`、专用 Prompt、`/api/reviewer/*` 及其初始化逻辑。
- 删除 `Reviewer.vue`、导航入口和 `REVIEWER_ENABLED` 配置。
- 删除仅用于该子产品的历史截图。
- 保留博客生成内部 `services.review.ReviewerAgent`、review guidelines、`reviewer_complete` SSE 事件和质量评估界面。
