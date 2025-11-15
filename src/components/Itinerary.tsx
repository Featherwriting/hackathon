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
        description: '探索旺角繁华商业街，体验香港特色文化和购物氛围。',
      },
      {
        id: 'a1-2',
        icon: '🍽️',
        title: '半包周年',
        time: '13:00 - 14:00 | 约1小时介绍',
        description: '品尝当地特色餐厅，享受地道港式美食。',
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
        description: '游览香港岛经典景点，感受城市风景和人文魅力。',
      },
      {
        id: 'a2-2',
        icon: '🌉',
        title: '大铁港城',
        time: '14:00 - 18:00 | 港澳介绍',
        description: '欣赏维港夜景，了解香港建筑文化。',
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
        description: '参观历史文化景点，深入了解香港历史背景。',
      },
      {
        id: 'a3-2',
        icon: '🏔️',
        title: '素办古镇',
        time: '13:00 - 16:30 | 约的古镇',
        description: '漫步古镇街道，感受古朴风情和传统工艺。',
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
        description: '登山远足，欣赏自然风光和全城美景。',
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
                    description: '更新后的旺角体验，新增特色购物路线。',
                  },
                  {
                    id: 'a1-2',
                    icon: '🍽️',
                    title: '米其林餐厅',
                    time: '13:00 - 15:00 | 约2小时',
                    description: '享受米其林星级美食，品尝顶级烹饪艺术。',
                  },
                  {
                    id: 'a1-3',
                    icon: '🎭',
                    title: '文化表演',
                    time: '19:00 - 21:00 | 约2小时',
                    description: '欣赏传统文化表演，体验香港艺术魅力。',
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
                    description: '在美丽沙滩放松身心，享受阳光和海风。',
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
