<template>
  <div class="title-section">
    <h1 class="blog-title">
      <span class="title-highlight">{{ title }}</span>
    </h1>
    <p v-if="description" class="blog-description">
      <span class="comment-prefix">// </span>{{ description }}
    </p>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title?: string
  description?: string
}

defineProps<Props>()
</script>

<style scoped>
.title-section {
  margin-bottom: 24px;
}

.blog-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 8px;
}

.title-highlight {
  background: linear-gradient(135deg, var(--text) 0%, var(--primary) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.blog-description {
  font-size: 14px;
  color: var(--text-secondary);
}

.comment-prefix {
  color: var(--string);
}

@media (max-width: 768px) {
  .blog-title {
    font-size: 1.5rem;
  }
}
</style>
