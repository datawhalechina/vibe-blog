# Changelog

All notable changes to the Vibe Blog project will be documented in this file.

---

## 2026.2.7

### Changes
- **Layout**: 首屏占满视口（PPT 翻页式），Hero + 输入框 flex 垂直居中，`min-height: calc(100vh - 60px)`。
- **Layout**: execute 按钮从底部工具栏移至输入框右侧，与 `$ find` 同行；`$ find` 垂直居中对齐。
- **Layout**: 底部工具栏精简，去掉 `Ctrl+Enter` 提示，只保留附件和高级选项。
- **Layout**: HeroSection padding 缩小适配首屏居中；副标题改为「一句话创作可发布的技术博客」。
- **History**: 分页组件替换为 SHOW MORE 追加加载模式。
- **Frontend**: 统一前端配色方案，对齐 main 分支。
- **Frontend**: 调整首页 Hero 区域上内距，标题和输入框下移。

### Added
- **Layout**: 底部 `scroll ↓` 提示动画，引导用户下滑查看历史记录。
- **History**: 滚动触发 `terminal-boot` 淡入上滑动画（0.8s）。
- **History**: 卡片打字机效果，每张卡片依次出现（间隔 120ms）。
- **Layout**: 高级选项面板绝对定位浮层 + CSS `slide-down` 过渡动画。
- **Test**: 完成前端 P1 组件集成测试。
- **Test**: Pinia Store 集成测试（37 tests, 92.82% 覆盖率）。
- **Test**: DatabaseService 单元测试（24 tests, 54.70% 覆盖率）。
- **Test**: 完整的自动化测试基础设施和前端 P0 单元测试。

### Fixes
- **Layout**: 高级选项展开/收起时 history 区域跳动问题（改为 `position: absolute` 脱离文档流）。
- **Frontend**: 修复前端功能 bug 对齐 main 分支。
- **Frontend**: 修复历史记录封面图片居中显示，补偿卡片 padding 宽度。

---

## 2026.2.6

### Fixes
- **Mini**: 更新 Mini 模式配置 - 章节数 2→4，配图数 3→5。

---

## 2026.2.5

### Added
- **Mini**: Mini 博客改造完成 - 动画视频生成和测试验证。(tag: v2.1.0-mini-blog-animation)
- **Mini**: `correct_section()` 方法 - Mini 模式只更正不扩展。
- **Mini**: 调试日志 - 每步 Prompt 字数和内容字数变化。
- **Test**: Mini 博客 v2 单元测试 - 字数统计、修订轮数限制、Prompt 日志。
- **Test**: 测试脚本添加文章保存功能。

### Fixes
- **Mini**: 限制 Mini 模式最多修订 1 轮。
- **Test**: 添加搜索服务初始化，修复背景知识为空的问题。
- **Test**: 添加图片服务初始化。

---

## 2026.2.4

### Added
- **Mini**: 实现 Mini 博客动画 v2 核心功能。

### Fixes
- **Test**: 修复测试脚本的返回值解析。

---

## 2026.1.31

### Fixes
- **Backend**: 图片水印/宽高比透传 + 日志清理 + 网络来源链接 + 视频方案。

---

## 2026.1.30

### Changes
- **Frontend**: 前端 UI 优化与 Docker 部署更新。
- **Frontend**: 优化 UI/UX：进度面板自适应、博客列表折叠按钮统计信息、输入框 Code Style 粒子背景。

### Added
- **CI**: 添加 GitHub Actions 自动构建前端。
- **Deploy**: 本地预构建前端，服务器直接部署静态文件。
- **Video**: 多图序列视频生成功能。

### Fixes
- **Deploy**: 添加 Node.js 内存限制避免服务器 OOM。
- **Frontend**: 修复 XhsCreator.vue 缺少关闭标签导致构建失败。

---

## 2026.1.28

### Changes
- **Frontend**: 优化终端侧边栏和博客卡片 UI。

---

## 2026.1.26

### Added
- **Video**: 集成 Sora2 视频服务和续创作模式（实验性）。
- **XHS**: 优化吉卜力模板 + 大纲生成 2000 字短文 + 修复发布功能。

---

## 2026.1.25

### Added
- **XHS**: 添加小红书生成服务和宫崎骏夏日漫画风格模板。

---

## 2026.1.23

### Added
- **Backend**: 添加 CSDN 一键发布功能 + 博客生成器改进。

---

## 2026.1.18

### Added
- **Backend**: 智能书籍聚合系统 - 博客自动组织成技术书籍。
- **Backend**: 添加图片生成重试机制和书籍处理进度日志。

### Fixes
- **Frontend**: 修复 Docsify 侧边栏重复问题，明确前后端分工。
- **Backend**: 修复数据库迁移顺序问题 - book_id 索引创建移到迁移之后。
- **Video**: 封面视频生成直接使用图片服务返回的外网 URL，跳过 OSS 上传。

---

## 2026.1.2

### Added
- **Backend**: 知识源二期 - 知识分块 + 两级结构 + 图片摘要。
- **Backend**: 实现自定义知识源整合一期功能。
- **Backend**: 实现多轮搜索能力。

### Fixes
- **Backend**: 提高审核通过阈值至 91 分，high 级别问题直接拦截。
- **Backend**: 添加防御性检查防止前置步骤失败导致后续 Agent 崩溃。

---

## 2025.12.31

### Added
- **Init**: Initial commit - Banana Vibe Blog Multi-Agent AI Blog Generator。
