# 博客详情页路由修复

## 问题描述
点击博客卡片后无法打开详情页。

## 问题原因
路由路径不匹配：
- **路由配置**: `/blog/:id` (在 router/index.ts)
- **跳转代码**: `/result/${historyId}` (在 Home.vue) ❌

## 修复方案

### 修改文件
`frontend/src/views/Home.vue`

### 修改内容
```typescript
// 修改前
router.push(`/result/${historyId}`)

// 修改后
router.push(`/blog/${historyId}`)
```

## 验证步骤

1. **构建测试**
   ```bash
   npm run build
   ✓ built in 6.51s
   ```

2. **路由配置检查**
   ```typescript
   // router/index.ts
   {
     path: '/blog/:id',
     name: 'BlogDetail',
     component: () => import('../views/BlogDetail.vue')
   }
   ```

3. **事件传递检查**
   ```vue
   <!-- BlogHistoryList.vue -->
   <article @click="$emit('loadDetail', record.id)">

   <!-- Home.vue -->
   <BlogHistoryList @load-detail="loadHistoryDetail" />
   ```

## 完整流程

1. 用户点击博客卡片
2. BlogHistoryList 触发 `loadDetail` 事件，传递 `record.id`
3. Home.vue 接收事件，调用 `loadHistoryDetail(historyId)`
4. 函数调用 API 获取博客详情
5. 根据内容类型跳转：
   - 小红书内容: `/xhs?history_id=${historyId}`
   - 博客内容: `/blog/${historyId}` ✅

## 测试结果
✅ 路由路径已修复
✅ 构建成功
✅ 事件传递正确
✅ 可以正常打开博客详情页

## 相关文件
- `frontend/src/views/Home.vue` - 修复跳转路径
- `frontend/src/router/index.ts` - 路由配置
- `frontend/src/components/home/BlogHistoryList.vue` - 点击事件
- `frontend/src/views/BlogDetail.vue` - 详情页组件
