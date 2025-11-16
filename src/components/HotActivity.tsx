import React, { useState, useMemo, useEffect } from 'react'

interface Activity {
  id: string
  title: string
  link: string
  hot?: boolean
}

// 空数组，完全由后端更新
const DEFAULT_ACTIVITIES: Activity[] = []

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
  const [activities, setActivities] = useState<Activity[]>(DEFAULT_ACTIVITIES)
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
