import { CopilotChat } from '@copilotkit/react-ui'
import './App.css'
import JourneyHeader from './components/JourneyHeader.tsx'
import HotActivity from './components/HotActivity.tsx'
import FeaturedSpots from './components/FeaturedSpots.tsx'
import Itinerary from './components/Itinerary.tsx'
import SocialMedia from './components/SocialMedia.tsx'
import { useFrontendActionsSetup } from './hooks/useFrontendActionsSetup.ts'
import { useCopilotResponseInterceptor } from './hooks/useCopilotResponseInterceptor.ts'

const CHAT_SUGGESTIONS = [
  { title: '查询评价', message: '媒体评分' },
  { title: '预定机票', message: '我想预定机票' },
]

export default function App() {
  // Setup frontend actions that AI agent can call
  useFrontendActionsSetup()
  
  // Intercept CopilotKit responses to automatically apply frontend updates
  useCopilotResponseInterceptor()

  return (
    <div className="app-container">
      {/* 左边：聊天框 */}
      <div className="chat-section">
        <CopilotChat
          labels={{ title: '旅游助手', initial: '你好👋，我能帮你做什么？' }}
          suggestions={CHAT_SUGGESTIONS}
        />
      </div>

      {/* 右边：旅程规划卡片 */}
      <div className="content-section">
        <JourneyHeader />

        <div className="hot-and-featured-row">
          <HotActivity />
          <FeaturedSpots />
        </div>

        <Itinerary />

        <SocialMedia />
      </div>
    </div>
  )
}