# Mermaid 图表渲染优化

## 问题描述
用户遇到 "Syntax error in text, mermaid version 10.9" 错误，导致博客详情页中的 Mermaid 图表无法正常显示。

## 优化方案

### 1. 增强错误处理

#### 优化前
```typescript
try {
  const { svg } = await mermaid.render(...)
  div.innerHTML = svg
} catch (e: any) {
  console.warn('Mermaid 图表渲染失败:', e.message)
  div.innerHTML = '<pre class="mermaid-error"><code>' + code + '</code></pre>'
}
```
- ❌ 简单的错误提示
- ❌ 没有详细的错误信息
- ❌ 没有调试帮助

#### 优化后
```typescript
try {
  const code = preprocessMermaidCode(originalCode)
  const { svg } = await mermaid.render(...)
  div.innerHTML = svg
} catch (e: any) {
  console.warn('Mermaid 图表渲染失败:', e.message, '\n原始代码:', originalCode)
  const errorDiv = createMermaidErrorBlock(originalCode, e.message)
  block.parentElement?.replaceWith(errorDiv)
}
```
- ✅ 详细的错误信息
- ✅ 显示原始代码
- ✅ 提供调试建议
- ✅ 美观的错误提示

### 2. 代码预处理优化

#### 新增功能
```typescript
const preprocessMermaidCode = (code: string): string => {
  // 1. 替换中文标点符号
  code = code.replace(/[""'']/g, '"')
  code = code.replace(/（/g, '(').replace(/）/g, ')')

  // 2. 修复空标签问题
  code = code.replace(/(\w+)\[""\]/g, '$1[" "]')

  // 3. 处理特殊字符
  code = code.replace(/\[([^\]]+)\]/g, (match, content) => {
    // 智能处理节点文本
  })

  // 4. 移除多余空行
  code = code.split('\n')
    .map(line => line.trim())
    .filter(line => line.length > 0)
    .join('\n')

  return code
}
```

### 3. 主题适配

#### 新增主题切换支持
```typescript
// 初始化时根据当前主题设置
mermaid.initialize({
  theme: isDark.value ? 'dark' : 'default',
  logLevel: 'error'
})

// 监听主题变化，自动重新渲染
watch(isDark, (newVal) => {
  mermaid.initialize({
    theme: newVal ? 'dark' : 'default'
  })
  renderMermaid()
})
```

### 4. 错误提示界面

#### 新的错误提示组件
```html
<div class="mermaid-error-container">
  <!-- 错误标题 -->
  <div class="mermaid-error-header">
    <svg>⚠️</svg>
    <span>Mermaid 图表渲染失败</span>
  </div>

  <!-- 错误信息 -->
  <div class="mermaid-error-message">
    <strong>错误信息:</strong> {errorMsg}
  </div>

  <!-- 原始代码（可折叠） -->
  <details class="mermaid-error-details">
    <summary>查看原始代码</summary>
    <pre><code>{code}</code></pre>
  </details>

  <!-- 调试建议 -->
  <div class="mermaid-error-tips">
    <strong>常见问题:</strong>
    <ul>
      <li>检查图表类型声明</li>
      <li>确保节点 ID 不包含特殊字符</li>
      <li>检查箭头语法</li>
      <li>确保引号、括号成对出现</li>
    </ul>
  </div>
</div>
```

## 优化效果

### 错误处理
- ✅ **详细错误信息**: 显示具体的错误原因
- ✅ **原始代码查看**: 可折叠的代码块，方便调试
- ✅ **调试建议**: 列出常见问题和解决方案
- ✅ **美观界面**: 使用设计 Token，与整体风格一致

### 用户体验
- ✅ **不会崩溃**: 即使图表语法错误，页面仍可正常显示
- ✅ **清晰提示**: 用户知道哪里出错了
- ✅ **易于调试**: 提供原始代码和错误信息
- ✅ **主题适配**: 自动适配深色/浅色模式

### 开发体验
- ✅ **控制台日志**: 输出详细的错误信息和原始代码
- ✅ **代码预处理**: 自动修复常见的语法问题
- ✅ **类型安全**: TypeScript 类型定义完整

## 样式优化

### 错误提示样式
```css
/* 错误容器 */
.mermaid-error-container {
  background: var(--color-error-light);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
}

/* 错误标题 */
.mermaid-error-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  color: var(--color-error);
  font-weight: var(--font-weight-semibold);
}

/* 错误信息 */
.mermaid-error-message {
  background: var(--color-bg-elevated);
  padding: var(--space-sm) var(--space-md);
  border-left: 3px solid var(--color-error);
}

/* 调试建议 */
.mermaid-error-tips {
  background: var(--color-info-light);
  border: 1px solid var(--color-info);
  border-radius: var(--radius-md);
}
```

## 常见 Mermaid 错误及解决方案

### 1. 语法错误
**错误**: `Syntax error in text`
**原因**: 图表类型声明错误或语法不正确
**解决**:
- 检查第一行是否正确声明图表类型
- 确保使用正确的语法格式

### 2. 特殊字符问题
**错误**: `Parse error on line X`
**原因**: 节点文本包含特殊字符
**解决**:
- 使用引号包裹包含特殊字符的文本
- 预处理会自动处理中文标点

### 3. 空标签问题
**错误**: `Empty label`
**原因**: 节点标签为空
**解决**:
- 确保所有节点都有标签
- 预处理会自动将空标签替换为空格

### 4. 箭头语法错误
**错误**: `Invalid arrow syntax`
**原因**: 使用了错误的箭头符号
**解决**:
- 使用正确的箭头语法 (-->, --->, ==>, etc.)
- 参考 Mermaid 官方文档

## 测试结果

### 构建测试
```bash
npm run build
✓ built in 6.55s
```

### 功能测试
- ✅ 正常图表渲染
- ✅ 错误图表显示友好提示
- ✅ 主题切换自动重新渲染
- ✅ 代码预处理修复常见问题
- ✅ 控制台输出详细日志

## 相关文件

- ✅ `frontend/src/views/BlogDetail.vue` - 已优化
  - Mermaid 初始化配置
  - 代码预处理函数
  - 错误提示组件
  - 主题适配逻辑
  - 样式优化

## 使用建议

### 对于用户
1. 如果看到错误提示，点击"查看原始代码"检查语法
2. 参考"常见问题"部分修复错误
3. 确保图表类型声明正确

### 对于开发者
1. 查看控制台日志获取详细错误信息
2. 使用预处理函数自动修复常见问题
3. 参考 Mermaid 官方文档编写正确的图表代码

## 后续优化建议

1. **在线编辑器**: 添加 Mermaid 图表在线编辑功能
2. **实时预览**: 编辑时实时预览图表效果
3. **模板库**: 提供常用图表模板
4. **语法检查**: 在保存前检查语法错误

---

**优化完成**: Mermaid 图表渲染更加健壮，错误提示更加友好！🎉
