import { useEffect } from 'react'
import { updateFeaturedSpots, type Spot } from '../components/FeaturedSpots.tsx'
import { updateItinerary, type DayPlan } from '../components/Itinerary.tsx'
import { updateSocialPosts, type SocialPost } from '../components/SocialMedia.tsx'

/**
 * Hook to setup frontend actions that the AI agent can call
 * This should be called within a component that's wrapped by CopilotKit provider
 */
export function useFrontendActionsSetup() {
  useEffect(() => {
    // Register frontend action handlers globally
    // These can be called by the backend Agent via the CopilotKit runtime
    
    // @ts-ignore - Adding to window for agent access
    window.__copilotkit_actions = {
      /**
       * Update featured spots/attractions
       * @param spots - Array of new spots to display
       */
      updateFeaturedSpots: async (spots: Spot[]) => {
        try {
          await updateFeaturedSpots(spots)
          console.log('Updated featured spots:', spots)
          return { success: true, message: 'Featured spots updated' }
        } catch (error) {
          console.error('Failed to update featured spots:', error)
          return { success: false, error: String(error) }
        }
      },

      /**
       * Update itinerary/day plans
       * @param plans - Array of day plans
       */
      updateItinerary: async (plans: DayPlan[]) => {
        try {
          await updateItinerary(plans)
          console.log('Updated itinerary:', plans)
          return { success: true, message: 'Itinerary updated' }
        } catch (error) {
          console.error('Failed to update itinerary:', error)
          return { success: false, error: String(error) }
        }
      },

      /**
       * Update social media posts
       * @param posts - Array of social posts
       */
      updateSocialPosts: async (posts: SocialPost[]) => {
        try {
          await updateSocialPosts(posts)
          console.log('Updated social posts:', posts)
          return { success: true, message: 'Social posts updated' }
        } catch (error) {
          console.error('Failed to update social posts:', error)
          return { success: false, error: String(error) }
        }
      },
    }

    return () => {
      // Cleanup
      // @ts-ignore
      window.__copilotkit_actions = undefined
    }
  }, [])
}
