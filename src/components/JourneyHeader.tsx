import React, { useState } from 'react'
import { DayPlan, updateItinerary } from './Itinerary.tsx'
import { Spot, updateFeaturedSpots } from './FeaturedSpots.tsx'
import { SocialPost, updateSocialPosts } from './SocialMedia.tsx'

const BASE_API = 'http://localhost:5000/api'

export default function JourneyHeader({ initialCity = '香港/HONGKONG' }: { initialCity?: string }) {
  const [city] = useState(initialCity)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [people, setPeople] = useState<number>(2)
  const [budget, setBudget] = useState<number>(0)
  const [loading, setLoading] = useState(false)

  async function handleUpdate() {
    // 前端兜底：必须先选好日期
    if (!startDate || !endDate) {
      alert('请先选择出发日期和返回日期')
      return
    }

    setLoading(true)

    try {
      // 1. 设置基础行程信息
      const baseInfoPayload = {
        userId: 'demo-user-1',
        cityName: city,
        cityCode: 'HKG',
        startDate,
        endDate,
        travelerCount: people,
        itineraryId: '',
      }

      const baseRes = await fetch(`${BASE_API}/itinerary/base-info`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(baseInfoPayload),
      })
      if (!baseRes.ok) {
        const errText = await baseRes.text()
        throw new Error(`base-info HTTP ${baseRes.status}: ${errText}`)
      }
      const baseData = await baseRes.json()
      const itineraryId = baseData.itineraryId as string

      // 2. 生成行程
      const genPayload = {
        userId: 'demo-user-1',
        itineraryId,
        cityName: city,
        cityCode: 'HKG',
        startDate,
        endDate,
        travelerCount: people,
        budgetAmount: budget,
      }

      const genRes = await fetch(`${BASE_API}/itinerary/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(genPayload),
      })
      if (!genRes.ok) {
        const errText = await genRes.text()
        throw new Error(`generate HTTP ${genRes.status}: ${errText}`)
      }
      const genData = await genRes.json()

      // 转成 Itinerary 需要的结构
      const newPlans: DayPlan[] = (genData.days || []).map((day: any) => ({
        id: `day-${day.dayIndex}`,
        day: `Day ${day.dayIndex}`,
        activities: (day.segments || []).map((seg: any) => {
          let icon = '📍'
          if (seg.segmentTypeCode === 'food') icon = '🍽️'
          else if (seg.segmentTypeCode === 'hotel') icon = '🏨'
          else if (seg.segmentTypeCode === 'flight') icon = '✈️'
          else if (seg.segmentTypeCode === 'transport') icon = '🚗'

          const hasTime = seg.startTime && seg.endTime
          const timeText = hasTime ? `${seg.startTime} - ${seg.endTime}` : '时间待定'

          return {
            id: seg.segmentId,
            icon,
            title: seg.title,
            time: timeText,
          }
        }),
      }))

      if (newPlans.length) {
        await updateItinerary(newPlans)
      }

      // 3. 景点列表 -> FeaturedSpots
      const poiPayload = {
        cityName: city,
        cityCode: 'HKG',
        categoryCode: 'photo_spot',
        pageNumber: 1,
        pageSize: 6,
        sortBy: 'recommend',
      }

      const poiRes = await fetch(`${BASE_API}/poi/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(poiPayload),
      })
      if (poiRes.ok) {
        const poiData = await poiRes.json()
        const newSpots: Spot[] = (poiData.items || []).slice(0, 4).map((item: any) => ({
          id: item.poiId,
          title: item.poiName,
          rating: item.ratingScore ?? 4.5,
          category: '热门景点',
          price: item.priceAmount ?? 0,
          image: item.coverImageUrl || 'https://via.placeholder.com/300x200?text=Spot',
        }))
        if (newSpots.length) {
          await updateFeaturedSpots(newSpots)
        }
      }

      // 4. 社交 Feed -> SocialMedia
      const feedPayload = {
        cityName: city,
        cityCode: 'HKG',
        sceneCode: 'itinerary_page',
        pageNumber: 1,
        pageSize: 8,
      }

      const feedRes = await fetch(`${BASE_API}/social/feed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedPayload),
      })
      if (feedRes.ok) {
        const feedData = await feedRes.json()
        const newPosts: SocialPost[] = (feedData.items || []).slice(0, 8).map((item: any) => ({
          id: item.postId,
          title: item.title,
          image: item.coverImageUrl || 'https://via.placeholder.com/150x150?text=Video',
          link: '#',
          platform: 'social',
        }))
        if (newPosts.length) {
          await updateSocialPosts(newPosts)
        }
      }

      alert('行程、景点、社交内容已从后端刷新')
    } catch (err) {
      console.error(err)
      alert('发送失败，请检查控制台或后端日志')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="journey-header">
      <h2>当前城市：{city}</h2>

      <div className="journey-form">
        <div className="field">
          <label>出发日期</label>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </div>

        <div className="field">
          <label>返回日期</label>
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </div>

        <div className="field">
          <label>出行人数</label>
          <input
            type="number"
            min={1}
            value={people}
            onChange={(e) => setPeople(Number(e.target.value))}
          />
        </div>

        <div className="field">
          <label>预算 (¥)</label>
          <input
            type="number"
            min={0}
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
          />
        </div>

        <div className="field actions">
          <button
            className="btn-update"
            onClick={handleUpdate}
            disabled={loading || !startDate || !endDate}
          >
            {loading ? '更新中...' : '更新需求'}
          </button>
        </div>
      </div>
    </div>
  )
}
