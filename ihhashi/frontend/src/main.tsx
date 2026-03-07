import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './lib/posthog' // Initialize PostHog analytics
import './lib/supabase' // Initialize Supabase client
import './lib/api' // Initialize API with CSRF protection
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
