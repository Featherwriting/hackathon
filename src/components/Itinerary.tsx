import React, { useState } from 'react'

export interface Activity {
  id: string
  icon: string
  title: string
  time: string
}

export interface DayPlan {
  id: string
  day: string
  activities: Activity[]
}

const DEFAULT_ITINERARY: DayPlan[] = [
  {
    id: 'day-1',
    day: 'Day 1',
    activities: [
      {
        id: 'a1-1',
        icon: '🗺️',
        title: '旺角太阳',
        time: '09:00 - 12:15 | 约3小时分钟',
      },
      {
        id: 'a1-2',
        icon: '🍽️',
        title: '半包周年',
        time: '13:00 - 14:00 | 约1小时介绍',
      },
    ],
  },
  {
    id: 'day-2',
    day: 'Day 2',
    activities: [
      {
        id: 'a2-1',
        icon: '🏮',
        title: '港岛玩乐品尝',
        time: '04:00 - 14:00 | 约5小时港澳活动',
      },
      {
        id: 'a2-2',
        icon: '🌉',
        title: '大铁港城',
        time: '14:00 - 18:00 | 港澳介绍',
      },
    ],
  },
  {
    id: 'day-3',
    day: 'Day 3',
    activities: [
      {
        id: 'a3-1',
        icon: '🏯',
        title: '新旺港岛1',
        time: '08:00 - 10:30 | 约2小时浏览',
      },
      {
        id: 'a3-2',
        icon: '🏔️',
        title: '素办古镇',
        time: '13:00 - 16:30 | 约的古镇',
      },
    ],
  },
  {
    id: 'day-4',
    day: 'Day 4',
    activities: [
      {
        id: 'a4-1',
        icon: '🏔️',
        title: '王岭山山',
        time: '08:00 - 12:00 | 山景的活动',
      },
    ],
  },
]

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
            <div key={activity.id} className="activity">
              <span>
                {activity.icon} {activity.title}
              </span>
              <span>{activity.time}</span>
            </div>
          ))}
        </div>
      ))}

      {/* 用于演示的更新按钮（开发模式） */}
      {process.env.NODE_ENV === 'development' && (
        <button
          className="btn-demo-update-itinerary"
          onClick={() => {
            const mockNewPlans: DayPlan[] = [
              {
                id: 'day-1',
                day: 'Day 1',
                activities: [
                  {
                    id: 'a1-1',
                    icon: '🗺️',
                    title: '旺角太阳（已更新）',
                    time: '09:00 - 12:15 | 约3小时',
                  },
                  {
                    id: 'a1-2',
                    icon: '🍽️',
                    title: '米其林餐厅',
                    time: '13:00 - 15:00 | 约2小时',
                  },
                  {
                    id: 'a1-3',
                    icon: '🎭',
                    title: '文化表演',
                    time: '19:00 - 21:00 | 约2小时',
                  },
                ],
              },
              {
                id: 'day-2',
                day: 'Day 2',
                activities: [
                  {
                    id: 'a2-1',
                    icon: '🏖️',
                    title: '沙滩休闲',
                    time: '08:00 - 12:00 | 约4小时',
                  },
                ],
              },
            ]
            updateItinerary(mockNewPlans)
          }}
          disabled={loading}
          style={{ marginTop: '12px' }}
        >
          {loading ? '更新中...' : '演示更新行程（开发模式）'}
        </button>
      )}
    </div>
  )
}
