import React, { useState } from 'react'

export interface Spot {
  id: string
  title: string
  rating: number
  category: string
  price: number
  image: string
}

const DEFAULT_SPOTS: Spot[] = [
  {
    id: 'spot-1',
    title: '港岛玩乐品尝',
    rating: 4.8,
    category: '港澳大地',
    price: 200,
    image: 'https://via.placeholder.com/300x200?text=Spot+1',
  },
  {
    id: 'spot-2',
    title: '千岛山山上日源泉',
    rating: 4.5,
    category: '活动大地',
    price: 320,
    image: 'https://via.placeholder.com/300x200?text=Spot+2',
  },
]

// 全局引用，用于外部更新景点
let globalUpdateSpots: ((spots: Spot[]) => Promise<void>) | null = null

export function updateFeaturedSpots(newSpots: Spot[]) {
  if (globalUpdateSpots) {
    return globalUpdateSpots(newSpots)
  }
  console.warn('FeaturedSpots component not yet mounted')
}

export default function FeaturedSpots() {
  const [spots, setSpots] = useState<Spot[]>(DEFAULT_SPOTS)
  const [loading, setLoading] = useState(false)

  // 注册更新函数供外部调用
  React.useEffect(() => {
    globalUpdateSpots = async (newSpots: Spot[]) => {
      setLoading(true)
      try {
        // 模拟后端延迟
        await new Promise((resolve) => setTimeout(resolve, 300))
        setSpots(newSpots)
        console.log('Spots updated:', newSpots)
      } catch (err) {
        console.error('Failed to update spots:', err)
      } finally {
        setLoading(false)
      }
    }
    return () => {
      globalUpdateSpots = null
    }
  }, [])

  return (
    <div className="featured-section">
      <div className="featured-cards">
        {spots.map((spot) => (
          <div key={spot.id} className="featured-card">
            <img src={spot.image} alt={spot.title} />
            <h3>{spot.title}</h3>
            <div className="rating">
              ⭐ {spot.rating} {spot.category} • 🏷️ {spot.price}
            </div>
            <button className="btn-book">立即订购</button>
          </div>
        ))}
      </div>

      {/* 用于演示的更新按钮（开发模式） */}
      {process.env.NODE_ENV === 'development' && (
        <button
          className="btn-demo-update"
          onClick={() => {
            const mockNewSpots: Spot[] = [
              {
                id: 'spot-3',
                title: '新增景点：维多利亚港夜景',
                rating: 4.9,
                category: '港澳体验',
                price: 150,
                image: 'https://via.placeholder.com/300x200?text=Victoria+Harbor',
              },
              {
                id: 'spot-1',
                title: '港岛玩乐品尝（已更新）',
                rating: 4.8,
                category: '港澳大地',
                price: 200,
                image: 'https://via.placeholder.com/300x200?text=Spot+1+Updated',
              },
            ]
            updateFeaturedSpots(mockNewSpots)
          }}
          disabled={loading}
        >
          {loading ? '更新中...' : '演示更新景点（开发模式）'}
        </button>
      )}
    </div>
  )
}

