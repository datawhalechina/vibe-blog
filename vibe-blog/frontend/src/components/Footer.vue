<template>
  <footer class="footer">
    <div class="footer-content">
      <p class="footer-info">
        <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" class="beian-link">京ICP备2026002630号-1</a>
        <span class="separator">|</span>
        <a href="https://www.beian.gov.cn/portal/index?token=" target="_blank" rel="noopener noreferrer" class="beian-link">京公网安备11010602202215号</a>
        <span class="separator">|</span>
        本作品采用 <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh" target="_blank" rel="noopener noreferrer" class="license-link">知识共享署名-非商业性使用-相同方式共享 4.0 国际许可协议</a> (CC BY-NC-SA 4.0) 进行许可
      </p>
    </div>
  </footer>
</template>

<script setup lang="ts">
</script>

<style scoped>
.footer {
  width: 100%;
  padding: 24px 16px;
  background: var(--color-muted);
  border-top: 1px solid var(--color-border);
  margin-top: 40px;
}

.footer-content {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
}

.footer-info {
  font-size: 12px;
  color: var(--color-muted-foreground);
  line-height: 1.6;
  margin: 0;
  word-break: break-word;
}

.beian-link,
.license-link {
  color: var(--color-info);
  text-decoration: underline;
  transition: color 0.2s ease;
  cursor: pointer;
}

.beian-link:hover,
.license-link:hover {
  color: var(--color-primary);
}

.separator {
  margin: 0 6px;
  color: var(--color-text-muted);
}

@media (max-width: 768px) {
  .footer {
    padding: 16px 12px;
  }

  .footer-info {
    font-size: 11px;
  }

  .separator {
    margin: 0 4px;
  }
}
</style>
