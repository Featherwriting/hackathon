import React, { useState } from 'react'

interface Activity {
  id: string
  title: string
  link: string
  hot?: boolean
}

interface Category {
  id: string
  label: string
}

const CATEGORIES: Category[] = [
  { id: 'popular', label: '美食盛宴' },
  { id: 'holiday', label: '节日热门' },
  { id: 'ai', label: 'AI推荐' },
  { id: 'shopping', label: '购物狂欢' },
  { id: 'event', label: '赛事活动' },
]

// 本地初始数据（作为兜底）
const LOCAL_ACTIVITIES_BY_CATEGORY: Record<string, Activity[]> = {
  popular: [
    { id: 'a1', title: 'BLAST香港 🔥', link: '#', hot: true },
    { id: 'a2', title: 'Mew演唱会2025香港站', link: '#' },
    { id: 'a3', title: '迪士尼万圣节特场', link: '#' },
    { id: 'a4', title: '香港赛马会', link: '#' },
    { id: 'a5', title: '最新快闪', link: '#' },
  ],
  holiday: [
    { id: 'b1', title: '圣诞节特惠活动', link: '#', hot: true },
    { id: 'b2', title: '跨年烟火庆典', link: '#' },
    { id: 'b3', title: '春节花灯展', link: '#' },
  ],
  ai: [
    { id: 'c1', title: 'AI餐厅推荐系统', link: '#', hot: true },
    { id: 'c2', title: '智能景点规划', link: '#' },
    { id: 'c3', title: 'AI助手定制旅程', link: '#' },
  ],
  shopping: [
    { id: 'd1', title: '双12购物节', link: '#', hot: true },
    { id: 'd2', title: '奢侈品折扣区', link: '#' },
    { id: 'd3', title: '手工艺品集市', link: '#' },
  ],
  event: [
    { id: 'e1', title: '港澳体育锦标赛', link: '#', hot: true },
    { id: 'e2', title: '音乐节周末', link: '#' },
    { id: 'e3', title: '文化艺术展', link: '#' },
  ],
}

const BASE_API = 'http://localhost:5000/api'

// 前端分类 id -> 后端 categoryCode 映射:contentReference[oaicite:4]{index=4}
const CATEGORY_CODE_MAP: Record<string, string> = {
  popular: 'ai_recommend',
  holiday: 'festival',
  ai: 'ai_recommend',
  shopping: 'shopping',
  event: 'sports',
}

export default function HotActivity() {
  const [activeCategory, setActiveCategory] = useState('popular')
  const [activities, setActivities] = useState<Activity[]>(LOCAL_ACTIVITIES_BY_CATEGORY['popular'])
  const [loading, setLoading] = useState(false)

  const handleTabClick = (id: string) => {
    setActiveCategory(id)
    setActivities(LOCAL_ACTIVITIES_BY_CATEGORY[id] || [])
  }

  // 真正调后端刷新内容
  const handleUpdateActivities = async () => {
    setLoading(true)
    try {
      const payload = {
        cityName: '香港',
        cityCode: 'HKG',
        timeRange: 'this_week',
        categoryCode: CATEGORY_CODE_MAP[activeCategory] || 'ai_recommend',
        pageNumber: 1,
        pageSize: 5,
      }

      const res = await fetch(`${BASE_API}/activity/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`activity/list HTTP ${res.status}`)
      const data = await res.json()

      const newActivities: Activity[] = (data.items || []).map((item: any) => ({
        id: item.activityId,
        title: item.title,
        link: '#',
        hot: true,
      }))

      if (newActivities.length) {
        setActivities(newActivities)
      }
    } catch (err) {
      console.error('Failed to fetch activities from backend, fallback to local data.', err)
      // 失败时继续用本地数据
      setActivities(LOCAL_ACTIVITIES_BY_CATEGORY[activeCategory] || [])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="hot-activity-section">
      <div className="activity-header">
        <h3>热门活动</h3>
        <select className="time-filter" defaultValue="week">
          <option value="week">本周</option>
          <option value="month">本月</option>
          <option value="all">全部</option>
        </select>
      </div>

      {/* 分类标签 */}
      <div className="category-tabs">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            className={`category-tab ${activeCategory === cat.id ? 'active' : ''}`}
            onClick={() => handleTabClick(cat.id)}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* 活动列表 */}
      <div className="news-list">
        {activities.map((activity) => (
          <div key={activity.id} className="news-item">
            <div className="news-content">
              {activity.hot && <span className="hot-badge">🔥</span>}
              <span className="news-title">{activity.title}</span>
            </div>
            <a href={activity.link} className="news-link">
              查看安排 →
            </a>
          </div>
        ))}
      </div>

      {/* 刷新按钮：现在会真正调用后端 */}
      <button className="btn-refresh" onClick={handleUpdateActivities} disabled={loading}>
        {loading ? '刷新中...' : '刷新内容'}
      </button>
    </div>
  )
}
