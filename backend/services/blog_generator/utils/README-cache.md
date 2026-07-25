# 缓存系统使用文档

## 概述

Researcher Agent 支持本地文件缓存机制，使用 **diskcache** 库实现，可以缓存搜索结果和 LLM 处理结果，避免重复调用 API，节省成本和时间。

**特点：**
- ✅ 纯本地缓存，无需外部服务
- ✅ 自动过期管理（TTL）
- ✅ 高性能磁盘缓存
- ✅ 零配置，开箱即用

## 快速开始

### 安装依赖

```bash
pip install diskcache
```

### 默认使用

无需任何配置，缓存已自动启用：

```bash
# 缓存目录：var/cache/
# 默认 TTL：24 小时
```

## 环境变量配置

### 缓存开关

```bash
# 启用/禁用 Researcher 缓存（默认启用）
RESEARCHER_CACHE_ENABLED=true
```

### 缓存过期时间

```bash
# 缓存 TTL（小时），默认 24 小时
CACHE_TTL_HOURS=24
```

## 缓存策略

### 缓存的内容

1. **搜索结果** (`search`)
   - 缓存键：topic + target_audience + max_results
   - 避免重复调用搜索 API

2. **智能搜索结果** (`smart_search`)
   - 缓存键：topic + target_audience + max_results
   - 避免重复调用多源搜索

3. **LLM 整理结果** (`summarize`)
   - 缓存键：topic + target_audience + search_depth + result_urls
   - 避免重复调用 LLM API

### 缓存过期时间

- 默认 TTL：24 小时
- 可通过环境变量配置：`CACHE_TTL_HOURS=48`
- 也可通过代码配置：

```python
from services.blog_generator.utils.cache_utils import init_cache_manager

# 设置 48 小时过期
init_cache_manager(ttl_hours=48)
```

## 使用示例

### 基本使用

缓存已自动集成到 Researcher Agent，无需修改代码：

```python
from services.blog_generator.agents.researcher import ResearcherAgent

# 创建 Researcher（自动启用缓存）
researcher = ResearcherAgent(llm_client, search_service)

# 第一次调用：从 API 获取数据并缓存
state = researcher.run({'topic': '什么是 RAG', 'target_audience': 'intermediate'})

# 第二次调用：直接从缓存读取（相同参数）
state = researcher.run({'topic': '什么是 RAG', 'target_audience': 'intermediate'})
```

### 手动管理缓存

```python
from services.blog_generator.utils.cache_utils import get_cache_manager

cache = get_cache_manager()

# 获取缓存统计
stats = cache.get_stats()
print(f"缓存统计: {stats}")
# 输出: {'backend': 'diskcache', 'total_keys': 15, 'cache_dir': '/path/to/cache', 'size_mb': 2.5}

# 清除特定前缀的缓存
cache.clear('search')  # 只清除搜索缓存

# 清除所有缓存
cache.clear()
```

### 禁用缓存

如果需要临时禁用缓存：

```bash
# 在 .env 中设置
RESEARCHER_CACHE_ENABLED=false
```

## 缓存命中日志

启用缓存后，日志中会显示缓存命中情况：

```
2026-02-09 23:30:00 - INFO - 💾 缓存管理器初始化: /path/to/cache, TTL=24h
2026-02-09 23:30:01 - INFO - 💾 Researcher 缓存已启用
2026-02-09 23:30:02 - INFO - ✅ 命中缓存: smart_search_abc123def456
2026-02-09 23:30:03 - INFO - 💾 缓存已保存: summarize_xyz789ghi012
```

## 性能对比

### 无缓存

```
搜索 + LLM 处理：~30-60 秒
API 成本：每次调用都产生费用
```

### 有缓存

```
首次：~30-60 秒（正常调用 + 写入缓存）
后续：<1 秒（直接读取缓存）
API 成本：仅首次调用产生费用
```

## 注意事项

1. **缓存目录**：
   - 缓存文件存储在 `var/cache/` 目录
   - diskcache 会自动管理缓存文件
   - 定期清理过期缓存以节省磁盘空间

2. **缓存失效**：
   - 修改搜索参数会生成新的缓存键
   - TTL 过期后自动失效
   - 可手动清除缓存

3. **性能**：
   - diskcache 使用 SQLite 作为索引，性能优秀
   - 支持并发读写
   - 自动处理缓存淘汰

## 故障排查

### diskcache 未安装

```
错误：diskcache 未安装，缓存功能将被禁用
解决：pip install diskcache
```

### 缓存未命中

```
原因：
1. 参数不完全相同（topic、target_audience 等）
2. 缓存已过期（超过 TTL）
3. 缓存被手动清除
```

### 磁盘空间不足

```
解决：
1. 手动清除缓存：cache.clear()
2. 减少 TTL 时间：CACHE_TTL_HOURS=12
3. 定期清理过期缓存
```

## 最佳实践

1. **开发环境**：使用默认配置，方便调试
2. **生产环境**：根据实际情况调整 TTL
3. **定期清理**：设置合理的 TTL，避免缓存堆积
4. **监控统计**：定期查看 `cache.get_stats()` 了解缓存使用情况

## diskcache 优势

相比自己实现的文件缓存，diskcache 提供：

- ✅ 自动过期管理（TTL）
- ✅ 并发安全（多进程/多线程）
- ✅ 高性能索引（SQLite）
- ✅ 自动缓存淘汰（LRU）
- ✅ 原子操作保证
- ✅ 缓存统计和监控

## 示例：查看缓存统计

```python
from services.blog_generator.utils.cache_utils import get_cache_manager

cache = get_cache_manager()
stats = cache.get_stats()

print(f"缓存后端: {stats['backend']}")
print(f"缓存数量: {stats['total_keys']}")
print(f"缓存大小: {stats['size_mb']} MB")
print(f"缓存目录: {stats['cache_dir']}")
```

输出：
```
缓存后端: diskcache
缓存数量: 15
缓存大小: 2.5 MB
缓存目录: /Users/xxx/vibe-blog/var/cache
```
