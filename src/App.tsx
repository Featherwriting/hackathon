import { CopilotChat } from '@copilotkit/react-ui'
import './App.css'
import JourneyHeader from './components/JourneyHeader.tsx'
import HotActivity from './components/HotActivity.tsx'
import FeaturedSpots from './components/FeaturedSpots.tsx'
import Itinerary from './components/Itinerary.tsx'
import SocialMedia from './components/SocialMedia.tsx'

export default function App() {
  return (
    <div className="app-container">
      {/* 左边：聊天框 */}
      <div className="chat-section">
        <CopilotChat
          instructions="你是一个中文助理。回答要准确、简洁。"
          labels={{ title: '助手', initial: '你好👋，我能帮你做什么？' }}
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