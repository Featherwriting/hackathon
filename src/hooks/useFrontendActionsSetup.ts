import { useEffect } from 'react'
import { updateFeaturedSpots, type Spot } from '../components/FeaturedSpots.tsx'
import { updateItinerary, type DayPlan } from '../components/Itinerary.tsx'
import { updateSocialPosts, type SocialPost } from '../components/SocialMedia.tsx'
import { updateTripInfo, type TripInfo } from '../components/JourneyHeader.tsx'

/**
 * Hook to setup frontend actions that the AI agent can call
 * This should be called within a component that's wrapped by CopilotKit provider
 * 
 * The backend LangGraph Agent will automatically call these functions
 * by passing data in the response extensions.frontendActions
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
          console.log('[Frontend Action] Updated featured spots:', spots)
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
          console.log('[Frontend Action] Updated itinerary:', plans)
          return { success: true, message: 'Itinerary updated' }
        } catch (error) {
          console.error('Failed to update itinerary:', error)
          return { success: false, error: String(error) }
        }
      },

      /**
       * Update trip information (destination, dates, people, budget, interests)
       * @param info - Trip information object
       */
      updateTripInfo: async (info: TripInfo) => {
        try {
          await updateTripInfo(info)
          console.log('[Frontend Action] Updated trip info:', info)
          return { success: true, message: 'Trip info updated' }
        } catch (error) {
          console.error('Failed to update trip info:', error)
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
          console.log('[Frontend Action] Updated social posts:', posts)
          return { success: true, message: 'Social posts updated' }
        } catch (error) {
          console.error('Failed to update social posts:', error)
          return { success: false, error: String(error) }
        }
      },

      /**
       * Update hot activities (city hotspots ranking)
       * @param items - Array of activity objects {id,title,link,hot}
       */
      updateHotActivities: async (items: any[]) => {
        try {
          // @ts-ignore will be provided by HotActivity component module export
          if (typeof window.__updateHotActivities === 'function') {
            // @ts-ignore
            window.__updateHotActivities(items)
          }
          console.log('[Frontend Action] Updated hot activities:', items)
          return { success: true, message: 'Hot activities updated' }
        } catch (error) {
          console.error('Failed to update hot activities:', error)
          return { success: false, error: String(error) }
        }
      },
    }

    // Also monitor for backend-triggered frontend updates
    // Listen for custom events if needed
    const handleFrontendUpdates = (event: any) => {
      const updates = event?.detail?.frontendActions
      if (updates) {
        if (updates.updateItinerary) {
          updateItinerary(updates.updateItinerary)
        }
        if (updates.updateTripInfo) {
          updateTripInfo(updates.updateTripInfo)
        }
        if (updates.updateFeaturedSpots) {
          updateFeaturedSpots(updates.updateFeaturedSpots)
        }
        if (updates.updateSocialPosts) {
          updateSocialPosts(updates.updateSocialPosts)
        }
        if (updates.updateHotActivities) {
          // @ts-ignore
          if (typeof window.__updateHotActivities === 'function') {
            // @ts-ignore
            window.__updateHotActivities(updates.updateHotActivities)
          }
        }
      }
    }

    // Dispatch custom event with updates (if available from response extensions)
    // @ts-ignore
    window.__copilotkit_apply_frontend_updates = (updates: any) => {
      if (updates?.updateItinerary) {
        updateItinerary(updates.updateItinerary)
      }
      if (updates?.updateTripInfo) {
        updateTripInfo(updates.updateTripInfo)
      }
      if (updates?.updateFeaturedSpots) {
        updateFeaturedSpots(updates.updateFeaturedSpots)
      }
      if (updates?.updateSocialPosts) {
        updateSocialPosts(updates.updateSocialPosts)
      }
      if (updates?.updateHotActivities) {
        // @ts-ignore
        if (typeof window.__updateHotActivities === 'function') {
          // @ts-ignore
          window.__updateHotActivities(updates.updateHotActivities)
        }
      }
    }

    return () => {
      // Cleanup
      // @ts-ignore
      window.__copilotkit_actions = undefined
      // @ts-ignore
      window.__copilotkit_apply_frontend_updates = undefined
    }
  }, [])
}
