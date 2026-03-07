import { useEffect } from 'react'
import posthog from '../lib/posthog'

/**
 * Hook to identify a user in PostHog
 * Call this after user logs in
 */
export function usePostHogIdentify(userId: string | null, traits?: Record<string, any>) {
  useEffect(() => {
    if (userId) {
      posthog.identify(userId, traits)
    } else {
      posthog.reset()
    }
  }, [userId, traits])
}

/**
 * Hook to track page views
 * PostHog auto-tracks, but this allows custom page names
 */
export function usePostHogPageView(pageName: string) {
  useEffect(() => {
    posthog.capture('$pageview', { page_name: pageName })
  }, [pageName])
}

/**
 * Capture a custom event
 */
export function captureEvent(eventName: string, properties?: Record<string, any>) {
  posthog.capture(eventName, properties)
}

/**
 * Set user properties
 */
export function setUserProperties(properties: Record<string, any>) {
  posthog.people.set(properties)
}

export default posthog
