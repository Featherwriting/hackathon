export interface BiliVideo {
  id: string
  title: string
  pic: string
  link: string
  playCount?: number
}

export async function searchBilibili(keyword: string, limit = 3): Promise<BiliVideo[]> {
  try {
    // 优先请求后端代理绝对地址，避免开发服务器未配置 /api 代理导致请求落空
    const apiBase = (typeof window !== 'undefined' && window.location && window.location.hostname === 'localhost') ? 'http://localhost:8000' : ''
    const url = `${apiBase}/api/bili_search?keyword=${encodeURIComponent(keyword)}&limit=${limit}`
    console.debug('[biliSearch] Proxy request URL:', url)
    const res = await fetch(url)
    console.debug('[biliSearch] Proxy HTTP status:', res.status, res.statusText)
    if (!res.ok) throw new Error(`proxy network ${res.status}`)
    const json = await res.json()

    const candidates: any[] = json?.videos || []

    const items = Array.isArray(candidates) ? candidates : []
    console.debug('[biliSearch] Candidate items count:', items.length)

    const videos = items
      .map((it: any) => {
        const bvid = it.bvid || it.id || (it.aid ? String(it.aid) : undefined) || Math.random().toString(36).slice(2)
        const title = it.title ? String(it.title).replace(/<[^>]+>/g, '') : it.title || ''
        const pic = it.pic || it.cover || ''
        const play = (it.stat && (it.stat.view || it.stat.play)) || it.play || it.playCount || 0
        const link = it.bvid ? `https://www.bilibili.com/video/${it.bvid}` : it.url || `https://www.bilibili.com/video/${bvid}`
        return {
          id: String(bvid),
          title,
          pic,
          link,
          playCount: Number(play) || 0,
        }
      })
      .filter(Boolean)

    videos.sort((a, b) => (b.playCount || 0) - (a.playCount || 0))
    const out = videos.slice(0, limit)
    console.debug('[biliSearch] Parsed videos (from proxy):', out)
    return out
  } catch (err) {
    console.error('[biliSearch] failed', err)
    return []
  }
}
