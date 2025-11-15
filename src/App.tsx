import { CopilotChat } from '@copilotkit/react-ui'
import './App.css'
import JourneyHeader from './components/JourneyHeader.tsx'
import HotActivity from './components/HotActivity.tsx'
import FeaturedSpots, { updateFeaturedSpots, type Spot } from './components/FeaturedSpots.tsx'
import Itinerary, { updateItinerary, type DayPlan } from './components/Itinerary.tsx'
import SocialMedia, { updateSocialPosts, type SocialPost } from './components/SocialMedia.tsx'
import { useFrontendActionsSetup } from './hooks/useFrontendActionsSetup.ts'

const CHAT_SUGGESTIONS = [
  { title: '查询评价', message: '查询景点评价' },
  { title: '获取推荐', message: '给我推荐景点' },
  { title: '行程规划', message: '帮我规划3天行程' },
  { title: '美食推荐', message: '推荐当地美食' },
  { title: '交通方式', message: '景点间的交通方式' },
  { title: '预算估算', message: '估算行程预算' },
]

export default function App() {
  // Setup frontend actions that AI agent can call
  useFrontendActionsSetup()

  // Frontend Actions - 让 Agent 能够更新前端 UI
  const handleUpdateSpots = async (spots: Spot[]) => {
    await updateFeaturedSpots(spots)
  }

  const handleUpdateItinerary = async (plans: DayPlan[]) => {
    await updateItinerary(plans)
  }

  const handleUpdateSocialPosts = async (posts: SocialPost[]) => {
    await updateSocialPosts(posts)
  }

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