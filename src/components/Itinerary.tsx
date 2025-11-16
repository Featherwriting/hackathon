import React, { useState } from 'react'

export interface Activity {
  id: string
  icon: string
  title: string
  time: string
  description?: string  // 新增：悬浮时显示的描述
}

export interface DayPlan {
  id: string
  day: string
  activities: Activity[]
}

const DEFAULT_ITINERARY: DayPlan[] = []  // 空数组，完全由后端更新

// 全局引用，用于外部更新行程
let globalUpdateItinerary: ((plans: DayPlan[]) => Promise<void>) | null = null

export function updateItinerary(newPlans: DayPlan[]) {
  if (globalUpdateItinerary) {
    return globalUpdateItinerary(newPlans)
  }
  console.warn('Itinerary component not yet mounted')
}

export default function Itinerary() {
  const [itinerary, setItinerary] = useState<DayPlan[]>(DEFAULT_ITINERARY)
  const [loading, setLoading] = useState(false)

  // 注册更新函数供外部调用
  React.useEffect(() => {
    globalUpdateItinerary = async (newPlans: DayPlan[]) => {
      setLoading(true)
      try {
        // 模拟后端延迟
        await new Promise((resolve) => setTimeout(resolve, 300))
        setItinerary(newPlans)
        console.log('Itinerary updated:', newPlans)
      } catch (err) {
        console.error('Failed to update itinerary:', err)
      } finally {
        setLoading(false)
      }
    }
    return () => {
      globalUpdateItinerary = null
    }
  }, [])

  return (
    <div className="itinerary-section">
      {itinerary.map((dayPlan) => (
        <div key={dayPlan.id} className="day-card">
          <h4>{dayPlan.day}</h4>
          {dayPlan.activities.map((activity) => (
            <div key={activity.id} className="activity-wrapper">
              <div className="activity">
                <span>
                  {activity.icon} {activity.title}
                </span>
                <span>{activity.time}</span>
              </div>
              {activity.description && (
                <div className="activity-description">
                  {activity.description}
                </div>
              )}
            </div>
          ))}
        </div>
      ))}

      
    </div>
  )
}
