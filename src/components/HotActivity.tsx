import React, { useState, useMemo, useEffect } from 'react'

interface Activity {
  id: string
  title: string
  link: string
  hot?: boolean
}

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

// 保留后端基址（暂不调用）
const BASE_API = 'http://localhost:5000/api'

// 将所有本地活动合并成一个列表，便于前端分页
const MERGED_LOCAL_ACTIVITIES: Activity[] = Object.values(LOCAL_ACTIVITIES_BY_CATEGORY).flat()

let externalSetter: ((items: Activity[]) => void) | null = null
export function updateHotActivities(items: Activity[]) {
  if (externalSetter) {
    externalSetter(items)
  }
}

// 在 window 注入供全局调用（被前端动作封装）
// @ts-ignore
if (typeof window !== 'undefined') window.__updateHotActivities = updateHotActivities

export default function HotActivity() {
  const [activities, setActivities] = useState<Activity[]>(MERGED_LOCAL_ACTIVITIES)
  const [page, setPage] = useState(1)
  const PAGE_SIZE = 5

  const totalPages = useMemo(() => Math.max(1, Math.ceil(activities.length / PAGE_SIZE)), [activities])
  const pagedActivities = useMemo(
    () => activities.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    [activities, page]
  )

  const goPrev = () => setPage((p) => Math.max(1, p - 1))
  const goNext = () => setPage((p) => Math.min(totalPages, p + 1))

  // 注册外部 setter
  useEffect(() => {
    externalSetter = (items: Activity[]) => {
      setActivities(items)
      setPage(1)
    }
    return () => {
      externalSetter = null
    }
  }, [])

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

      {/* 活动列表（分页后仅显示当前页） */}
      <div className="news-list">
        {pagedActivities.map((activity) => (
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

      {/* 分页控件 */}
      <div className="pagination-container">
        <button className="page-btn" onClick={goPrev} disabled={page === 1}>
          ← 上一页
        </button>
        <div className="page-dots">
          {Array.from({ length: totalPages }).map((_, idx) => {
            const current = idx + 1
            return (
              <span
                key={current}
                className={`page-dot ${current === page ? 'active' : ''}`}
                onClick={() => setPage(current)}
              />
            )
          })}
        </div>
        <button className="page-btn" onClick={goNext} disabled={page === totalPages}>
          下一页 →
        </button>
      </div>
    </div>
  )
}

// 移除旧的外部更新逻辑（已用 useEffect 注入）
