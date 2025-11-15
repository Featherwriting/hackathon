import React, { useState } from 'react'
/* 新增：导入本地图片 1-5 */
import pic1 from './pic/1.png'
import pic2 from './pic/2.png'
import pic3 from './pic/3.png'
import pic4 from './pic/4.png'
import pic5 from './pic/5.png'
import pic6 from './pic/6.png'
import pic7 from './pic/7.png'
import pic8 from './pic/8.png'

export interface SocialPost {
  id: string
  title: string
  image: string
  link: string
  platform?: string
}

const DEFAULT_POSTS: SocialPost[] = []

// 全局引用，用于外部更新社交媒体内容
type UpdateArg = SocialPost[] | ((prev: SocialPost[]) => SocialPost[])
let globalUpdateSocialPosts: ((posts: UpdateArg, mode?: 'replace' | 'prepend' | 'append') => Promise<void>) | null = null

// 挂起队列：当组件尚未挂载时缓存更新请求
const pendingUpdates: { posts: UpdateArg; mode: 'replace' | 'prepend' | 'append' }[] = []

export function updateSocialPosts(newPosts: UpdateArg, mode: 'replace' | 'prepend' | 'append' = 'replace') {
  if (globalUpdateSocialPosts) {
    return globalUpdateSocialPosts(newPosts, mode)
  }
  // 组件未挂载，入队等待
  pendingUpdates.push({ posts: newPosts, mode })
  console.log('SocialMedia not mounted yet — queued update', { mode, queued: pendingUpdates.length })
  return Promise.resolve()
}

export default function SocialMedia() {
  const [posts, setPosts] = useState<SocialPost[]>(DEFAULT_POSTS)
  const [loading, setLoading] = useState(false)

  // 注册更新函数供外部调用
  React.useEffect(() => {
    globalUpdateSocialPosts = async (newPosts: UpdateArg, mode: 'replace' | 'prepend' | 'append' = 'replace') => {
      setLoading(true)
      try {
        // 模拟后端延迟
        await new Promise((resolve) => setTimeout(resolve, 300))
        setPosts((prev) => {
          // 支持函数式更新
          if (typeof newPosts === 'function') {
            try {
              return (newPosts as (p: SocialPost[]) => SocialPost[])(prev)
            } catch (e) {
              console.error('updateSocialPosts function threw', e)
              return prev
            }
          }
          const arr = newPosts as SocialPost[]
          if (mode === 'replace') return arr
          if (mode === 'prepend') return [...arr, ...prev]
          return [...prev, ...arr]
        })
        console.log('Social posts updated:', newPosts)
      } catch (err) {
        console.error('Failed to update social posts:', err)
      } finally {
        setLoading(false)
      }
    }
    // 组件挂载后，立即应用任何挂起的更新
    if (pendingUpdates.length) {
      ;(async () => {
        for (const u of pendingUpdates.splice(0)) {
          try {
            await globalUpdateSocialPosts?.(u.posts, u.mode)
          } catch (e) {
            console.error('Failed to apply queued social update', e)
          }
        }
      })()
    }

    return () => {
      globalUpdateSocialPosts = null
    }
  }, [])

  return (
    <div className="social-section">
      <h4>
        B站视频
        <span style={{ marginLeft: 8, fontSize: 12, color: '#888' }}>(BiliSearch 结果)</span>
      </h4>
      <div className="social-posts">
        {posts.length === 0 ? (
          <div style={{ padding: '12px 8px', color: '#666' }}>尚无 B 站搜索结果（请在聊天中指定目的地触发搜索）</div>
        ) : (
          posts.map((post) => (
            <a key={post.id} href={post.link} className="social-post-card" target="_blank" rel="noopener noreferrer">
              <div className="post-image">
                <img src={post.image} alt={post.title} onError={(e) => { (e.target as HTMLImageElement).src = '/static/media/placeholder.png' }} />
              </div>
              <div className="post-title">
                {post.title}
                {post.platform === 'bilibili' && (
                  <span style={{ marginLeft: 8, fontSize: 12, color: '#ff4d4f' }}>B站</span>
                )}
              </div>
              { (post as any).playCount !== undefined && (
                <div style={{ fontSize: 12, color: '#999', marginTop: 6 }}>{(post as any).playCount} 次播放</div>
              )}
            </a>
          ))
        )}
      </div>

      {/* 用于演示的更新按钮（开发模式） */}
      {process.env.NODE_ENV === 'development' && (
        <button
          className="btn-demo-update-social"
          onClick={() => {
            const mockNewPosts: SocialPost[] = [
              {
                id: 'post-6',
                title: '最新港澳景点推荐',
                image: pic6,
                link: '#',
                platform: 'xiaohongshu',
              },
              {
                id: 'post-2',
                title: '美食节活动现场',
                image: pic2,
                link: '#',
                platform: 'xiaohongshu',
              },
              {
                id: 'post-7',
                title: '旅行穿搭灵感',
                image: pic7,
                link: '#',
                platform: 'xiaohongshu',
              },
              {
                id: 'post-8',
                title: '酒店豪华体验',
                image: pic8,
                link: '#',
                platform: 'xiaohongshu',
              },
            ]
            updateSocialPosts(mockNewPosts)
          }}
          disabled={loading}
          style={{ marginTop: '12px' }}
        >
          {loading ? '更新中...' : '演示更新内容（开发模式）'}
        </button>
      )}
    </div>
  )
}
