import React, { useState } from 'react'

export interface Spot {
  id: string
  title: string
  rating: number
  category: string
  price: number
}

const DEFAULT_SPOTS: Spot[] = []  // 空数组，完全由后端更新

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
            <h3>{spot.title}</h3>
            <div className="rating">
              ⭐ {spot.rating} {spot.category} • 🏷️ {spot.price}
            </div>
            <button className="btn-book">立即订购</button>
          </div>
        ))}
      </div>
    </div>
  )
}

