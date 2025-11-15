import { CopilotChat } from '@copilotkit/react-ui'
import './App.css'

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
        <div className="journey-header">
          <h2>当前城市：香港/HONGKONG</h2>
          <div className="header-info">
            <span>📅 2025/12/15-12/20</span>
            <span>👥 2人</span>
            <span>💰 11233人</span>
          </div>
        </div>

        {/* 热门活动标签 */}
        <div className="activity-tabs">
          <button className="tab-active">热门行动</button>
          <button className="tab">节日周末</button>
          <button className="tab">入境</button>
          <button className="tab">网路餐厅</button>
          <button className="tab">最重要的</button>
        </div>

        {/* 热点选择和图片展示 */}
        <div className="featured-section">
          <div className="featured-cards">
            <div className="featured-card">
              <img src="https://via.placeholder.com/300x200" alt="Featured 1" />
              <h3>港岛玩乐品尝</h3>
              <div className="rating">⭐ 4.8 港澳大地 • 🏷️ 200</div>
              <button className="btn-book">立即订购</button>
            </div>
            <div className="featured-card">
              <img src="https://via.placeholder.com/300x200" alt="Featured 2" />
              <h3>千岛山山上日源泉</h3>
              <div className="rating">⭐ 4.5 活动大地 • 🏷️ 320</div>
              <button className="btn-book">立即订购</button>
            </div>
          </div>
        </div>

        {/* 行程规划天数 */}
        <div className="itinerary-section">
          <div className="day-card">
            <h4>Day 1</h4>
            <div className="activity">
              <span>🗺️ 旺角太阳</span>
              <span>09:00 - 12:15 | 约3小时分钟</span>
            </div>
            <div className="activity">
              <span>🍽️ 半包周年</span>
              <span>13:00 - 14:00 | 约1小时介绍</span>
            </div>
          </div>

          <div className="day-card">
            <h4>Day 2</h4>
            <div className="activity">
              <span>🏮 港岛玩乐品尝</span>
              <span>04:00 - 14:00 | 约5小时港澳活动</span>
            </div>
            <div className="activity">
              <span>🌉 大铁港城</span>
              <span>14:00 - 18:00 | 港澳介绍</span>
            </div>
          </div>

          <div className="day-card">
            <h4>Day 3</h4>
            <div className="activity">
              <span>🏯 新旺港岛1</span>
              <span>08:00 - 10:30 | 约2小时浏览</span>
            </div>
            <div className="activity">
              <span>🏔️ 素办古镇</span>
              <span>13:00 - 16:30 | 约的古镇</span>
            </div>
          </div>

          <div className="day-card">
            <h4>Day 4</h4>
            <div className="activity">
              <span>🏔️ 王岭山山</span>
              <span>08:00 - 12:00 | 山景的活动</span>
            </div>
          </div>
        </div>

        {/* 社交分享 */}
        <div className="social-section">
          <h4>联网视频</h4>
          <div className="social-links">
            <a href="#" className="social-link">Google</a>
          </div>
        </div>
      </div>
    </div>
  )
}