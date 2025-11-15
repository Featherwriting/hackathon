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

const DEFAULT_POSTS: SocialPost[] = [
  {
    id: 'post-1',
    title: '港澳美食探险',
    image: pic2, // 使用 2.png
    link: '#',
    platform: 'xiaohongshu',
  },
  {
    id: 'post-2',
    title: '维港夜景打卡',
    image: pic1, // 使用 1.png
    link: '#',
    platform: 'xiaohongshu',
  },
  {
    id: 'post-3',
    title: '迪士尼乐园攻略',
    image: pic3, // 使用 3.png
    link: '#',
    platform: 'xiaohongshu',
  },
  {
    id: 'post-4',
    title: '购物街推荐',
    image: pic4, // 使用 4.png
    link: '#',
    platform: 'xiaohongshu',
  },
  {
    id: 'post-5',
    title: '文化艺术展览',
    image: pic5, // 使用 5.png
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
