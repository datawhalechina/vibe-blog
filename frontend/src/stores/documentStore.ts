import { create } from 'zustand'

// 章节数据结构
export interface Section {
  index: number
  title: string
  content: string
  status: 'pending' | 'generating' | 'complete'
}

// 大纲数据结构
export interface Outline {
  title: string
  summary?: string
  sections: Section[]
}

interface DocumentState {
  // 文档信息
  documentId: string | null
  title: string
  markdown: string
  
  // 大纲和章节（实时更新用）
  outline: Outline | null
  
  // 生成结果
  coverUrl: string | null
  videoUrl: string | null
  
  // 操作
  setDocument: (doc: { id?: string; title?: string; markdown?: string }) => void
  setMarkdown: (markdown: string) => void
  setCoverUrl: (url: string | null) => void
  setVideoUrl: (url: string | null) => void
  
  // 大纲和章节操作
  setOutline: (outline: Outline) => void
  updateSection: (index: number, updates: Partial<Section>) => void
  setSectionContent: (index: number, content: string) => void
  
  reset: () => void
}

export const useDocumentStore = create<DocumentState>((set) => ({
  documentId: null,
  title: '新建博客',
  markdown: '',
  outline: null,
  coverUrl: null,
  videoUrl: null,

  setDocument: (doc) =>
    set((state) => ({
      documentId: doc.id ?? state.documentId,
      title: doc.title ?? state.title,
      markdown: doc.markdown ?? state.markdown,
    })),

  setMarkdown: (markdown) => set({ markdown }),

  setCoverUrl: (url) => set({ coverUrl: url }),

  setVideoUrl: (url) => set({ videoUrl: url }),

  setOutline: (outline) => set({ outline, title: outline.title }),

  updateSection: (index, updates) =>
    set((state) => {
      if (!state.outline) return state
      const sections = [...state.outline.sections]
      if (sections[index]) {
        sections[index] = { ...sections[index], ...updates }
      }
      return { outline: { ...state.outline, sections } }
    }),

  setSectionContent: (index, content) =>
    set((state) => {
      if (!state.outline) return state
      const sections = [...state.outline.sections]
      if (sections[index]) {
        sections[index] = { ...sections[index], content, status: 'complete' }
      }
      return { outline: { ...state.outline, sections } }
    }),

  reset: () =>
    set({
      documentId: null,
      title: '新建博客',
      markdown: '',
      outline: null,
      coverUrl: null,
      videoUrl: null,
    }),
}))
