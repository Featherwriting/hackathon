import { CopilotChat } from '@copilotkit/react-ui'

export default function App() {
  return (
    <div style={{ maxWidth: 720, margin: '40px auto', padding: 16 }}>
      <h1>CopilotKit UI示例</h1>
      <CopilotChat
        instructions="你是一个中文助理。回答要准确、简洁。"
        labels={{ title: '助手', initial: '你好👋，我能帮你做什么？' }}
      />
    </div>
  )
}