import React, { useState, useEffect } from 'react'

export interface TripInfo {
  destination: string
  startDate: string
  endDate: string
  people: number
  budget: string
  interests: string[]
}

const DEFAULT_INFO: TripInfo = {
  destination: '',
  startDate: '',
  endDate: '',
  people: 0,
  budget: '',
  interests: []
}

// 全局引用，用于外部更新旅行信息
let globalUpdateTripInfo: ((info: TripInfo) => Promise<void>) | null = null

export function updateTripInfo(newInfo: TripInfo) {
  if (globalUpdateTripInfo) {
    return globalUpdateTripInfo(newInfo)
  }
  console.warn('JourneyHeader component not yet mounted')
}

export default function JourneyHeader() {
  const [tripInfo, setTripInfo] = useState<TripInfo>(DEFAULT_INFO)

  // 注册更新函数供外部调用
  useEffect(() => {
    globalUpdateTripInfo = async (newInfo: TripInfo) => {
      try {
        setTripInfo(newInfo)
        console.log('Trip info updated:', newInfo)
      } catch (err) {
        console.error('Failed to update trip info:', err)
      }
    }
    return () => {
      globalUpdateTripInfo = null
    }
  }, [])

  // 如果没有旅行信息，显示提示
  if (!tripInfo.destination) {
    return (
      <div className="journey-header">
        <h2>✨ 开始规划您的旅程</h2>
        <div className="header-info">
          <span>💬 在左侧聊天框中告诉我您的旅行需求</span>
        </div>
      </div>
    )
  }

  return (
    <div className="journey-header">
      <h2>📍 {tripInfo.destination}</h2>
      <div className="header-info">
        {tripInfo.startDate && tripInfo.endDate && (
          <span>📅 {tripInfo.startDate} 至 {tripInfo.endDate}</span>
        )}
        {tripInfo.people > 0 && (
          <span>👥 {tripInfo.people} 人</span>
        )}
        {tripInfo.budget && (
          <span>💰 预算：{tripInfo.budget}</span>
        )}
        {tripInfo.interests && tripInfo.interests.length > 0 && (
          <span>🎯 兴趣：{tripInfo.interests.join('、')}</span>
        )}
      </div>
    </div>
  )
}
