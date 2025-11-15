import React, { useState } from 'react'

const API_URL = 'https://example.com/api/updateRequirements' // <- 替换为真实 API

export default function JourneyHeader({ initialCity = '香港/HONGKONG' }: { initialCity?: string }) {
  const [city] = useState(initialCity)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [people, setPeople] = useState<number>(2)
  const [budget, setBudget] = useState<number>(0)
  const [loading, setLoading] = useState(false)

  async function handleUpdate() {
    setLoading(true)
    const payload = { city, startDate, endDate, people, budget }
    try {
      const res = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      // 如果需要处理返回值，可以在这里解析：const data = await res.json()
      alert('已成功发送需求更新（示例）。请在控制台查看网络请求或替换 API_URL 为真实接口。')
    } catch (err) {
      // 错误处理留空或简单提示
      console.error(err)
      alert('发送失败，请检查控制台或更新 API_URL。')
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
          <input type="number" min={1} value={people} onChange={(e) => setPeople(Number(e.target.value))} />
        </div>

        <div className="field">
          <label>预算 (¥)</label>
          <input type="number" min={0} value={budget} onChange={(e) => setBudget(Number(e.target.value))} />
        </div>

        <div className="field actions">
          <button className="btn-update" onClick={handleUpdate} disabled={loading}>
            {loading ? '更新中...' : '更新需求'}
          </button>
        </div>
      </div>
    </div>
  )
}
