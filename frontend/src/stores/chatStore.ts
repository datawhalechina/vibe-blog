import { create } from 'zustand'
import type { ChatMessage, ExecutionLogItem } from '@/types'

interface ChatState {
  messages: ChatMessage[]
  executionLogs: ExecutionLogItem[]
  isGenerating: boolean
  
  addMessage: (message: ChatMessage) => void
  addExecutionLog: (log: ExecutionLogItem) => void
  updateExecutionLog: (id: string, updates: Partial<ExecutionLogItem>) => void
  setIsGenerating: (value: boolean) => void
  clearLogs: () => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  executionLogs: [],
  isGenerating: false,

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  addExecutionLog: (log) =>
    set((state) => ({
      executionLogs: [...state.executionLogs, log],
    })),

  updateExecutionLog: (id, updates) =>
    set((state) => ({
      executionLogs: state.executionLogs.map((log) =>
        log.id === id ? { ...log, ...updates } as ExecutionLogItem : log
      ),
    })),

  setIsGenerating: (value) => set({ isGenerating: value }),

  clearLogs: () => set({ executionLogs: [] }),

  clearMessages: () => set({ messages: [] }),
}))
