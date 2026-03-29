<template>
  <div class="min-h-screen bg-background text-foreground">
    <!-- Fixed Top Navigation -->
    <header class="fixed top-0 left-0 right-0 z-50 backdrop-blur-md border-b bg-card/95 border-border">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo -->
          <router-link to="/" class="flex items-center gap-3 group">
            <div class="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-primary/10 border-primary/20">
              <div class="w-2 h-2 rounded-full animate-pulse bg-primary"></div>
              <span class="text-xs font-mono font-semibold text-primary">ONLINE</span>
            </div>
            <div class="font-sans text-lg flex items-center font-bold">
              <span class="text-primary">~/</span>
              <span class="ml-1 text-foreground">vibe-blog</span>
              <span class="inline-block w-2 h-5 ml-1 animate-blink bg-primary"></span>
            </div>
          </router-link>

          <!-- Navigation -->
          <nav class="hidden md:flex items-center gap-2">
            <a href="#" class="px-4 py-2 rounded-lg font-mono text-sm transition-all duration-200 cursor-pointer text-secondary-foreground hover:text-foreground hover:bg-muted">
              <span class="text-muted-foreground">$</span>
              <span class="ml-2 text-[var(--color-syntax-function)]">cd</span>
              <span class="ml-2">/categories</span>
            </a>
            <a href="#" class="px-4 py-2 rounded-lg font-mono text-sm border transition-all duration-200 cursor-pointer bg-primary/10 text-primary border-primary/20 hover:bg-primary/20">
              <span class="text-muted-foreground">$</span>
              <span class="font-semibold ml-2">ai</span>
              <span class="ml-2">--search</span>
            </a>
          </nav>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="pt-28 pb-20 px-4 sm:px-6 lg:px-8">
      <div class="max-w-7xl mx-auto">
        <!-- Search Section -->
        <section class="mb-10">
          <div class="rounded-xl overflow-hidden shadow-card border bg-card border-border hover:border-primary/50 transition-colors duration-300">
            <!-- Terminal Header -->
            <div class="flex items-center justify-between px-4 py-3 border-b bg-muted border-border">
              <div class="flex items-center gap-3">
                <div class="flex items-center gap-2">
                  <div class="w-3 h-3 rounded-full bg-[var(--color-dot-red)]"></div>
                  <div class="w-3 h-3 rounded-full bg-[var(--color-dot-yellow)]"></div>
                  <div class="w-3 h-3 rounded-full bg-[var(--color-dot-green)]"></div>
                </div>
                <span class="text-xs font-mono text-muted-foreground">search.sh</span>
              </div>
              <button
                @click="searchQuery = ''"
                class="text-xs font-mono text-muted-foreground hover:text-primary transition-colors duration-200 cursor-pointer"
              >
                [clear]
              </button>
            </div>
            <!-- Terminal Body -->
            <div class="p-6">
              <div class="flex items-center gap-3 font-mono text-sm">
                <span class="text-base text-muted-foreground">❯</span>
                <span class="font-semibold text-[var(--color-syntax-keyword)]">find</span>
                <input
                  v-model="searchQuery"
                  type="text"
                  :placeholder="`搜索 ${mockBlogs.length} 篇博客...`"
                  class="flex-1 bg-transparent outline-none border-none text-foreground placeholder:text-muted-foreground"
                />
              </div>
            </div>
          </div>
        </section>

        <!-- Stats Bar -->
        <section class="mb-10">
          <div class="flex items-center justify-between flex-wrap gap-4 rounded-xl p-5 border bg-muted border-border">
            <div class="flex items-center gap-3 font-mono text-sm">
              <span class="text-muted-foreground">❯</span>
              <span class="text-muted-foreground">count:</span>
              <span class="text-lg font-bold text-primary">{{ filteredBlogs.length }}</span>
              <span class="text-secondary-foreground">篇博客</span>
              <span class="text-muted-foreground ml-2">--sort-by</span>
            </div>
            <div class="flex items-center gap-2 flex-wrap">
              <button
                v-for="sort in sortOptions"
                :key="sort.value"
                @click="currentSort = sort.value"
                :class="[
                  'px-4 py-2 rounded-lg font-mono text-sm transition-all duration-200 cursor-pointer',
                  currentSort === sort.value
                    ? 'bg-primary text-primary-foreground shadow-[var(--shadow-primary)]'
                    : 'bg-secondary text-secondary-foreground border border-border hover:bg-[var(--color-bg-hover)] hover:text-foreground hover:border-[var(--color-border-hover)]'
                ]"
              >
                <span class="mr-2">{{ sort.icon }}</span>
                {{ sort.label }}
              </button>
            </div>
          </div>
        </section>

        <!-- Blog Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          <div
            v-for="blog in filteredBlogs"
            :key="blog.id"
            class="group cursor-pointer animate-fade-up"
          >
            <div class="rounded-xl overflow-hidden shadow-card hover:shadow-card-hover hover:-translate-y-2 transition-all duration-300 border h-full flex flex-col bg-card border-border hover:border-primary group-hover:shadow-[0_20px_40px_-12px_rgba(139,92,246,0.25)]">
              <!-- Terminal Header -->
              <div class="flex items-center justify-between px-4 py-3 border-b bg-muted border-border">
                <div class="flex items-center gap-3">
                  <div class="flex items-center gap-1.5">
                    <div class="w-2.5 h-2.5 rounded-full bg-[var(--color-dot-red)] group-hover:bg-[var(--color-dot-red-hover)] transition-colors duration-200"></div>
                    <div class="w-2.5 h-2.5 rounded-full bg-[var(--color-dot-yellow)] group-hover:bg-[var(--color-dot-yellow-hover)] transition-colors duration-200"></div>
                    <div class="w-2.5 h-2.5 rounded-full bg-[var(--color-dot-green)] group-hover:bg-[var(--color-dot-green-hover)] transition-colors duration-200"></div>
                  </div>
                  <span class="text-xs font-mono text-muted-foreground">{{ blog.filename }}</span>
                </div>
                <div class="flex items-center gap-1">
                  <span v-for="i in blog.stars" :key="i" class="text-xs">⭐</span>
                </div>
              </div>

              <!-- Card Content -->
              <div class="p-6 flex-1 flex flex-col">
                <div class="font-mono text-sm space-y-3 mb-5">
                  <!-- Line 1: export -->
                  <div class="flex items-start gap-3">
                    <span class="select-none w-6 text-right flex-shrink-0 text-muted-foreground">1</span>
                    <div class="flex-1 leading-relaxed">
                      <span class="font-semibold text-[var(--color-syntax-keyword)]">export</span>
                      <span class="ml-2 font-semibold text-foreground">{{ blog.title }}</span>
                    </div>
                  </div>
                  <!-- Line 2: comment -->
                  <div class="flex items-start gap-3">
                    <span class="select-none w-6 text-right flex-shrink-0 text-muted-foreground">2</span>
                    <div class="flex-1 leading-relaxed">
                      <span class="text-[var(--color-syntax-comment)]">// {{ blog.description }}</span>
                    </div>
                  </div>
                  <!-- Line 3: from author -->
                  <div class="flex items-start gap-3">
                    <span class="select-none w-6 text-right flex-shrink-0 text-muted-foreground">3</span>
                    <div class="flex-1 leading-relaxed">
                      <span class="font-semibold text-[var(--color-syntax-import)]">from</span>
                      <span class="ml-2 text-[var(--color-syntax-string)]">"{{ blog.author }}"</span>
                    </div>
                  </div>
                  <!-- Line 4: empty -->
                  <div class="flex items-start gap-3">
                    <span class="select-none w-6 text-right flex-shrink-0 text-muted-foreground">4</span>
                    <div class="flex-1 h-4"></div>
                  </div>
                </div>

                <!-- Tags -->
                <div class="flex flex-wrap gap-2 mb-5">
                  <span
                    v-for="tag in blog.tags"
                    :key="tag"
                    class="px-3 py-1.5 text-xs font-mono rounded border transition-all duration-200 cursor-pointer bg-primary/10 text-primary border-primary/20 hover:bg-primary/20 hover:border-primary"
                  >
                    #{{ tag }}
                  </span>
                </div>

                <!-- Footer -->
                <div class="mt-auto pt-4 border-t flex items-center justify-between border-border">
                  <div class="flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold bg-gradient-to-br from-primary to-[var(--color-syntax-keyword)] text-primary-foreground">
                      {{ blog.author[0] }}
                    </div>
                    <span class="text-xs font-mono text-secondary-foreground">{{ blog.author }}</span>
                  </div>
                  <div class="flex items-center gap-2 group-hover:translate-x-1 transition-transform duration-200 text-primary">
                    <span class="text-sm">→</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="filteredBlogs.length === 0" class="mt-16">
          <div class="rounded-xl overflow-hidden shadow-card border max-w-2xl mx-auto bg-card border-[var(--color-error)]">
            <div class="flex items-center gap-3 px-4 py-3 border-b bg-muted border-[var(--color-error)]">
              <div class="flex items-center gap-2">
                <div class="w-3 h-3 rounded-full bg-[var(--color-dot-red)]"></div>
                <div class="w-3 h-3 rounded-full bg-[var(--color-dot-yellow)]"></div>
                <div class="w-3 h-3 rounded-full bg-[var(--color-dot-green)]"></div>
              </div>
              <span class="text-xs font-mono text-muted-foreground">error.log</span>
            </div>
            <div class="p-10 text-center">
              <div class="font-mono text-sm space-y-4">
                <p class="text-lg font-bold text-[var(--color-error)]">❌ Error: No blogs found</p>
                <p class="text-[var(--color-syntax-comment)]">// 没有找到匹配的博客</p>
                <p class="text-muted-foreground">// 尝试调整搜索关键词或清除筛选条件</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const searchQuery = ref('')
const currentSort = ref('stars')

const sortOptions = [
  { value: 'stars', label: '热门', icon: '⭐' },
  { value: 'recent', label: '最新', icon: '🕐' }
]

const mockBlogs = [
  {
    id: 1,
    title: 'ModernWebDev',
    description: '现代 Web 开发完整指南',
    author: 'Alice Chen',
    filename: 'modern-web.ts',
    stars: 5,
    tags: ['react', 'typescript', 'vite'],
    date: '2026-02-05'
  },
  {
    id: 2,
    title: 'Vue3Mastery',
    description: 'Vue 3 组合式 API 深度解析',
    author: 'Bob Zhang',
    filename: 'vue3-guide.vue',
    stars: 5,
    tags: ['vue', 'composition-api', 'pinia'],
    date: '2026-02-04'
  },
  {
    id: 3,
    title: 'AIIntegration',
    description: '将 AI 集成到你的应用中',
    author: 'Carol Liu',
    filename: 'ai-integration.md',
    stars: 4,
    tags: ['ai', 'openai', 'langchain'],
    date: '2026-02-03'
  },
  {
    id: 4,
    title: 'TailwindPro',
    description: 'Tailwind CSS 专业实践',
    author: 'David Wang',
    filename: 'tailwind-pro.css',
    stars: 4,
    tags: ['tailwind', 'css', 'design'],
    date: '2026-02-02'
  },
  {
    id: 5,
    title: 'TypeScriptPatterns',
    description: 'TypeScript 高级设计模式',
    author: 'Eve Li',
    filename: 'ts-patterns.ts',
    stars: 5,
    tags: ['typescript', 'patterns', 'advanced'],
    date: '2026-01-01'
  },
  {
    id: 6,
    title: 'PerformanceOpt',
    description: 'Web 应用性能优化实战',
    author: 'Frank Zhou',
    filename: 'performance.js',
    stars: 4,
    tags: ['performance', 'optimization', 'web-vitals'],
    date: '2026-01-31'
  }
]


const filteredBlogs = computed(() => {
  let blogs = mockBlogs

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    blogs = blogs.filter(blog =>
      blog.title.toLowerCase().includes(query) ||
      blog.description.toLowerCase().includes(query) ||
      blog.author.toLowerCase().includes(query) ||
      blog.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  if (currentSort.value === 'stars') {
    blogs = [...blogs].sort((a, b) => b.stars - a.stars)
  } else if (currentSort.value === 'recent') {
    blogs = [...blogs].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  }

  return blogs
})
</script>
