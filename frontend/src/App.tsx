import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { Navbar } from './components/Layout/Navbar'
import { LeftPanel } from './components/Chat/LeftPanel'
import { RightPanel } from './components/Editor/RightPanel'
import { useBlogGeneration } from './hooks/useBlogGeneration'

function App() {
  const { generate } = useBlogGeneration()

  const handleSendMessage = async (message: string) => {
    try {
      // 解析用户输入，提取主题
      // 简单处理：整个消息作为主题
      await generate({
        topic: message,
        article_type: 'tutorial',
        target_length: 'mini',  // 默认使用 mini 模式快速测试
      })
    } catch (error) {
      console.error('Generate blog error:', error)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      <Navbar title="新建博客" saveStatus="saved" />
      
      <div className="flex-1 overflow-hidden">
        <PanelGroup direction="horizontal">
          {/* Left Panel - Editor */}
          <Panel defaultSize={70} minSize={50}>
            <RightPanel />
          </Panel>
          
          {/* Resize Handle */}
          <PanelResizeHandle className="w-1 bg-gray-200 hover:bg-vibe-orange/50 transition-colors cursor-col-resize" />
          
          {/* Right Panel - Chat & Execution Log */}
          <Panel defaultSize={30} minSize={25} maxSize={40}>
            <LeftPanel onSendMessage={handleSendMessage} />
          </Panel>
        </PanelGroup>
      </div>
    </div>
  )
}

export default App
