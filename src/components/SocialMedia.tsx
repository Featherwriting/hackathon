import React, { useState } from 'react'

export interface SocialPost {
  id: string
  title: string
  image: string
  link: string
  platform?: string
}

const DEFAULT_POSTS: SocialPost[] = [
  {
    id: 'post-1',
    title: '港澳美食探险',
    image: 'https://via.placeholder.com/150x150?text=Food+1',
    link: '#',
    platform: 'xiaohongshu',
  },
  {
    id: 'post-2',
    title: '维港夜景打卡',
    image: 'https://via.placeholder.com/150x150?text=Harbor',
    link: '#',
    platform: 'xiaohongshu',
  },
  {
    id: 'post-3',
    title: '迪士尼乐园攻略',
    image: 'https://via.placeholder.com/150x150?text=Disney',
    link: '#',
    platform: 'xiaohongshu',
  },
  {
    id: 'post-4',
    title: '购物街推荐',
    image: 'https://via.placeholder.com/150x150?text=Shopping',
    link: '#',
    platform: 'xiaohongshu',
  },
  {
    id: 'post-5',
    title: '文化艺术展览',
    image: 'https://via.placeholder.com/150x150?text=Art',
    link: '#',
    platform: 'xiaohongshu',
  },
]

// 全局引用，用于外部更新社交媒体内容
let globalUpdateSocialPosts: ((posts: SocialPost[]) => Promise<void>) | null = null

export function updateSocialPosts(newPosts: SocialPost[]) {
  if (globalUpdateSocialPosts) {
    return globalUpdateSocialPosts(newPosts)
  }
  console.warn('SocialMedia component not yet mounted')
}

export default function SocialMedia() {
  const [posts, setPosts] = useState<SocialPost[]>(DEFAULT_POSTS)
  const [loading, setLoading] = useState(false)

  // 注册更新函数供外部调用
  React.useEffect(() => {
    globalUpdateSocialPosts = async (newPosts: SocialPost[]) => {
      setLoading(true)
      try {
        // 模拟后端延迟
        await new Promise((resolve) => setTimeout(resolve, 300))
        setPosts(newPosts)
        console.log('Social posts updated:', newPosts)
      } catch (err) {
        console.error('Failed to update social posts:', err)
      } finally {
        setLoading(false)
      }
    }
    return () => {
      globalUpdateSocialPosts = null
    }
  }, [])

  return (
    <div className="social-section">
      <h4>联网视频</h4>
      <div className="social-posts">
        {posts.map((post) => (
          <a key={post.id} href={post.link} className="social-post-card">
            <div className="post-image">
              <img src={post.image} alt={post.title} />
            </div>
            <div className="post-title">{post.title}</div>
          </a>
        ))}
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
                image: 'https://via.placeholder.com/150x150?text=New+1',
                link: '#',
                platform: 'xiaohongshu',
              },
              {
                id: 'post-7',
                title: '美食节活动现场',
                image: 'https://via.placeholder.com/150x150?text=New+2',
                link: '#',
                platform: 'xiaohongshu',
              },
              {
                id: 'post-8',
                title: '旅行穿搭灵感',
                image: 'https://via.placeholder.com/150x150?text=New+3',
                link: '#',
                platform: 'xiaohongshu',
              },
              {
                id: 'post-9',
                title: '酒店豪华体验',
                image: 'https://via.placeholder.com/150x150?text=New+4',
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
