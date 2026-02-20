---
name: problem-solution
description: 问题解决型文章写作技能。当用户要求写踩坑记录、问题排查、故障处理类文章时使用。产出结构为问题描述、排查过程、解决方案、经验总结。
license: MIT
allowed-tools: zhipu-search, serper-google, jina-reader
---

# 问题解决型文章写作技能

## 适用场景
- 用户要求写 "XXX 踩坑记录"、"解决 XXX 问题"
- 文章类型为 problem-solution / troubleshooting / debugging

## 写作方法论

### Phase 1: 问题定义
- 精确描述问题现象（错误信息、复现步骤）
- 说明影响范围和严重程度
- 列出环境信息（版本、配置）

### Phase 2: 排查过程
- 按时间线记录排查步骤
- 每步记录：假设 → 验证方法 → 结果
- 展示关键日志和调试输出

### Phase 3: 解决方案
- 给出最终解决方案（代码/配置变更）
- 解释根因（为什么会出现这个问题）
- 提供替代方案（如果有）

### Phase 4: 经验总结
- 提炼可复用的排查方法论
- 列出预防措施
- 关联相关问题
