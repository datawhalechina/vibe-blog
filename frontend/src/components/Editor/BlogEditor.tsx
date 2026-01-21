import { useEffect, useRef } from 'react'
import { useCreateBlockNote } from '@blocknote/react'
import { BlockNoteView } from '@blocknote/mantine'
import { MantineProvider } from '@mantine/core'
import { useEditorStore } from '@/stores/editorStore'
import { useDocumentStore } from '@/stores/documentStore'
import { markdownToBlocks } from '@/utils/markdownToBlocks'

export function BlogEditor() {
  const { setContext } = useEditorStore()
  const { markdown, outline } = useDocumentStore()
  const prevMarkdownRef = useRef<string>('')
  const prevOutlineRef = useRef<string>('')
  
  const editor = useCreateBlockNote({
    initialContent: [
      {
        type: "heading",
        props: { level: 1 },
        content: [{ type: "text", text: "欢迎使用 Vibe Blog 2.0", styles: {} }],
      },
      {
        type: "paragraph",
        content: [
          { type: "text", text: "在左侧输入你的博客主题，AI 将帮你生成专业的技术博客。", styles: {} }
        ],
      },
      {
        type: "paragraph",
        content: [
          { type: "text", text: "你可以：", styles: {} }
        ],
      },
      {
        type: "bulletListItem",
        content: [{ type: "text", text: "拖拽调整段落顺序", styles: {} }],
      },
      {
        type: "bulletListItem",
        content: [{ type: "text", text: "点击段落添加配图、图表、代码等", styles: {} }],
      },
      {
        type: "bulletListItem",
        content: [{ type: "text", text: "使用 AI 优化任意段落内容", styles: {} }],
      },
    ],
  })

  // 当大纲变化时，更新编辑器内容（实时显示章节）
  useEffect(() => {
    if (outline) {
      const outlineKey = JSON.stringify(outline)
      if (outlineKey !== prevOutlineRef.current) {
        prevOutlineRef.current = outlineKey
        
        // 构建 blocks：标题 + 每个章节
        const blocks: any[] = [
          {
            id: 'title-block',
            type: 'heading',
            props: { level: 1, textColor: 'default', backgroundColor: 'default', textAlignment: 'left' },
            content: [{ type: 'text', text: outline.title, styles: {} }],
            children: [],
          },
        ]

        // 添加每个章节
        outline.sections.forEach((section, index) => {
          // 章节标题
          blocks.push({
            id: `section-title-${index}`,
            type: 'heading',
            props: { level: 2, textColor: 'default', backgroundColor: 'default', textAlignment: 'left' },
            content: [{ type: 'text', text: section.title, styles: {} }],
            children: [],
          })

          // 章节内容或占位符
          if (section.content) {
            // 有内容 - 解析 markdown 并添加
            const contentBlocks = markdownToBlocks(section.content)
            contentBlocks.forEach((block, blockIndex) => {
              block.id = `section-${index}-content-${blockIndex}`
              blocks.push(block)
            })
          } else {
            // 无内容 - 显示状态
            const statusText = section.status === 'generating' 
              ? '⏳ 正在生成...' 
              : section.status === 'pending'
              ? '⏸️ 等待生成...'
              : ''
            
            if (statusText) {
              blocks.push({
                id: `section-${index}-placeholder`,
                type: 'paragraph',
                props: { textColor: 'gray', backgroundColor: 'default', textAlignment: 'left' },
                content: [{ type: 'text', text: statusText, styles: { italic: true } }],
                children: [],
              })
            }
          }
        })

        try {
          editor.replaceBlocks(editor.document, blocks)
        } catch (error) {
          console.error('Failed to update editor with outline:', error)
        }
      }
    }
  }, [outline, editor])

  // 当最终 markdown 变化时，更新编辑器内容（完成后的完整内容）
  useEffect(() => {
    if (markdown && markdown !== prevMarkdownRef.current && !outline) {
      prevMarkdownRef.current = markdown
      try {
        const blocks = markdownToBlocks(markdown)
        if (blocks.length > 0) {
          editor.replaceBlocks(editor.document, blocks)
        }
      } catch (error) {
        console.error('Failed to convert markdown to blocks:', error)
      }
    }
  }, [markdown, outline, editor])

  // Update context when editor changes
  const handleEditorChange = () => {
    const blocks = editor.document
    setContext({
      totalBlocks: blocks.length,
    })
  }

  return (
    <MantineProvider>
      <div className="h-full overflow-y-auto bg-white">
        <div className="max-w-4xl mx-auto py-8 px-4">
          <BlockNoteView 
            editor={editor} 
            onChange={handleEditorChange}
            theme="light"
          />
        </div>
      </div>
    </MantineProvider>
  )
}
