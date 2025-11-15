/**
 * Hook to intercept CopilotKit chat responses and apply frontend updates
 * This automatically processes any frontendActions returned by the backend
 */

import { useEffect } from 'react'
import { updateFeaturedSpots, type Spot } from '../components/FeaturedSpots.tsx'
import { updateItinerary, type DayPlan } from '../components/Itinerary.tsx'
import { updateSocialPosts, type SocialPost } from '../components/SocialMedia.tsx'
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
