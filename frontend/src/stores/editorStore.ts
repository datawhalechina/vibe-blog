import { create } from 'zustand'
import type { EditorContext, BlockViewState } from '@/types'

interface EditorState {
  context: EditorContext
  blockViews: Map<string, BlockViewState>
  
  setContext: (context: Partial<EditorContext>) => void
  setBlockView: (blockId: string, view: BlockViewState['currentView']) => void
  setBlockThinking: (blockId: string, thinking: string) => void
}

export const useEditorStore = create<EditorState>((set) => ({
  context: {
    totalBlocks: 0,
    currentBlockIndex: 0,
  },
  blockViews: new Map(),

  setContext: (context) =>
    set((state) => ({
      context: { ...state.context, ...context },
    })),

  setBlockView: (blockId, view) =>
    set((state) => {
      const newBlockViews = new Map(state.blockViews)
      const existing = newBlockViews.get(blockId) || { blockId, currentView: 'preview' }
      newBlockViews.set(blockId, { ...existing, currentView: view })
      return { blockViews: newBlockViews }
    }),

  setBlockThinking: (blockId, thinking) =>
    set((state) => {
      const newBlockViews = new Map(state.blockViews)
      const existing = newBlockViews.get(blockId) || { blockId, currentView: 'preview' }
      newBlockViews.set(blockId, { ...existing, thinkingContent: thinking })
      return { blockViews: newBlockViews }
    }),
}))
