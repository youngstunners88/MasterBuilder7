import posthog from 'posthog-js'

// PostHog analytics - ONLY initialize if key is provided via environment variable
// NEVER hardcode keys - they can be scraped and used to pollute your analytics
const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY;
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://app.posthog.com';

// Only initialize if key is properly configured
if (POSTHOG_KEY && POSTHOG_KEY !== 'your_posthog_key_here' && !POSTHOG_KEY.startsWith('zo_sk_')) {
  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    // Enable session recording for UX insights
    session_recording: {
      maskAllInputs: false,
      maskInputOptions: {
        password: true, // Always mask password fields
      },
    },
    // Capture page views automatically
    capture_pageview: true,
    // Persist user sessions
    persistence: 'localStorage',
  });
} else {
  console.warn('PostHog not initialized: VITE_POSTHOG_KEY not configured or using placeholder value');
}

export default posthog
