/**
 * Hook to intercept CopilotKit chat responses and apply frontend updates
 * This automatically processes any frontendActions returned by the backend
 */

import { useEffect } from 'react'
import { updateFeaturedSpots, type Spot } from '../components/FeaturedSpots.tsx'
import { updateItinerary, type DayPlan } from '../components/Itinerary.tsx'
import { updateSocialPosts, type SocialPost } from '../components/SocialMedia.tsx'
import { searchBilibili } from '../utils/biliSearch.ts'
import { updateHotActivities } from '../components/HotActivity.tsx'

export function useCopilotResponseInterceptor() {
  useEffect(() => {
    // Intercept the original fetch to monitor CopilotKit responses
    const originalFetch = window.fetch

    window.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const response = await originalFetch(input, init)

      // Check if this is a CopilotKit response
      const url = input instanceof URL ? input.toString() : typeof input === 'string' ? input : ''
      if (url.includes('/copilotkit_remote')) {
        // Clone response for processing
        const responseClone = response.clone()

        try {
          const data = await responseClone.json()
          const frontendActions = data?.data?.generateCopilotResponse?.extensions?.frontendActions

          if (frontendActions) {
            console.log('[Response Interceptor] Processing frontend actions:', frontendActions)

            // Apply each frontend action
            if (frontendActions.updateItinerary && Array.isArray(frontendActions.updateItinerary)) {
              console.log('[Response Interceptor] Updating itinerary with:', frontendActions.updateItinerary)
              updateItinerary(frontendActions.updateItinerary as DayPlan[])
            }

            if (frontendActions.updateFeaturedSpots && Array.isArray(frontendActions.updateFeaturedSpots)) {
              console.log('[Response Interceptor] Updating featured spots with:', frontendActions.updateFeaturedSpots)
              updateFeaturedSpots(frontendActions.updateFeaturedSpots as Spot[])
            }

            if (frontendActions.updateSocialPosts && Array.isArray(frontendActions.updateSocialPosts)) {
              console.log('[Response Interceptor] Updating social posts with:', frontendActions.updateSocialPosts)
              updateSocialPosts(frontendActions.updateSocialPosts as SocialPost[])
            }

            if (frontendActions.updateHotActivities && Array.isArray(frontendActions.updateHotActivities)) {
              console.log('[Response Interceptor] Updating hot activities with:', frontendActions.updateHotActivities)
              updateHotActivities(frontendActions.updateHotActivities)
            }
          }

          // 无论是否存在 frontendActions，都尝试从响应中提取关键词并查询 B 站（取热度前三）
          try {
            console.log('[Response Interceptor] Attempting to extract keywords/destination for Bili search')

            // 辅助：递归提取字符串内容
            function extractText(obj: any, out: string[]) {
              if (!obj) return
              if (typeof obj === 'string') {
                out.push(obj)
                return
              }
              if (typeof obj === 'number' || typeof obj === 'boolean') return
              if (Array.isArray(obj)) {
                for (const v of obj) extractText(v, out)
                return
              }
              if (typeof obj === 'object') {
                for (const k of Object.keys(obj)) extractText(obj[k], out)
              }
            }

            const texts: string[] = []
            extractText(data, texts)
            const joined = texts.filter(Boolean).join('\n')

            // 优先尝试从响应文本中显式提取目的地（destination）信息
            function extractDestination(text: string): string | null {
              if (!text) return null
              // 常见格式：目的地：香港 / 目的地是香港 / 目的地 - 香港
              const re1 = /目的地\s*(?:是|:|：|-|——)?\s*([\u4e00-\u9fff·\w\-]{2,20})/i
              const m1 = text.match(re1)
              if (m1 && m1[1]) return m1[1].trim()

              // 又或者：去香港、去澳门
              const re2 = /去([\u4e00-\u9fff·\w\-]{2,20})/i
              const m2 = text.match(re2)
              if (m2 && m2[1]) return m2[1].trim()

              // 作为兜底，从首个出现频率高的关键词里挑一个看起来像城市名的词
              const kwRe = /[\u4e00-\u9fff]{2,6}/g
              const matches = text.match(kwRe) || []
              if (matches.length) return matches[0] || null

              return null
            }

            const destination = extractDestination(joined)
            let searchKey: string | null = null
            if (destination) {
              searchKey = destination
              console.log('[Response Interceptor] Destination extracted for Bili search:', searchKey)
            } else {
              // 简单关键词抽取：优先匹配 2-6 个中文字符的短语
              function extractKeywordsFromChinese(text: string, limit = 5) {
                const re = /[\u4e00-\u9fff]{2,6}/g
                const matches = text.match(re) || []
                const freq: Record<string, number> = {}
                for (const m of matches) {
                  freq[m] = (freq[m] || 0) + 1
                }
                return Object.entries(freq)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, limit)
                  .map((p) => p[0])
              }

              const keywords = extractKeywordsFromChinese(joined, 5)
              if (keywords.length > 0) searchKey = keywords[0]
              if (searchKey) console.log('[Response Interceptor] Fallback keyword for Bili search:', searchKey)
            }

            if (searchKey) {
              console.log('[Response Interceptor] Performing Bili search for:', searchKey)
              const videos = await searchBilibili(searchKey, 3)
              console.log('[Response Interceptor] Bili search returned:', videos)
              if (videos && videos.length) {
                const socialPosts: SocialPost[] = videos.map((v) => ({
                  id: `bili-${v.id}`,
                  title: v.title || searchKey!,
                  image: v.pic || '',
                  link: v.link || `https://www.bilibili.com/video/${v.id}`,
                  platform: 'bilibili',
                }))
                console.log('[Response Interceptor] Updating social posts with Bili results (replace):', socialPosts)
                // 将 B 站结果替换掉现有社媒列表内容
                updateSocialPosts(socialPosts, 'replace')
              } else {
                console.log('[Response Interceptor] No videos returned from Bili search for:', searchKey)
              }
            } else {
              console.log('[Response Interceptor] No search key extracted from response')
            }
          } catch (err) {
            console.debug('[Response Interceptor] Bili search or keyword extraction failed', err)
          }
        } catch (error) {
          console.debug('[Response Interceptor] Could not parse response as JSON (expected for non-CopilotKit requests)')
        }
      }

      return response
    }) as typeof fetch

    return () => {
      // Restore original fetch on cleanup
      window.fetch = originalFetch
    }
  }, [])
}
