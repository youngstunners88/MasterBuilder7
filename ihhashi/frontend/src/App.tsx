import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect, createContext, useContext } from 'react'
import * as Sentry from '@sentry/react'

import Home from './pages/Home'
import Auth from './pages/auth/Auth'
import Products from './pages/catalog/Products'
import { CartPage } from './pages/CartPage'
import { CheckoutPage } from './pages/CheckoutPage'
import { OrderTrackingPage } from './pages/OrderTrackingPage'
import { MerchantPage } from './pages/MerchantPage'
import { MerchantDashboard } from './pages/MerchantDashboard'
import { MerchantRegistrationPage } from './pages/MerchantRegistrationPage'
import { RiderDashboard } from './pages/RiderDashboard'
import { DriverRegistrationPage } from './pages/DriverRegistrationPage'
import { PaymentSuccessPage } from './pages/PaymentSuccessPage'
import { NotFoundPage } from './pages/NotFoundPage'
import Orders from './pages/orders/Orders'
import Profile from './pages/profile/Profile'
import { RewardsDashboard, ReferralPage } from './pages/rewards'
import ErrorBoundary from './components/common/ErrorBoundary'
import SplashScreen from './components/SplashScreen'
import { authAPI } from './lib/api'

// Only init Sentry if DSN is set via env — never hardcode credentials
const GLITCHTIP_DSN = import.meta.env.VITE_GLITCHTIP_DSN
if (GLITCHTIP_DSN) {
  Sentry.init({
    dsn: GLITCHTIP_DSN,
    tracesSampleRate: 0.2,
    environment: import.meta.env.MODE || 'development',
  })
}

// ─── Auth Context ────────────────────────────────────────────────────────────
interface AuthUser {
  id: string
  email?: string
  phone: string
  full_name?: string
  role: string
}

interface AuthContextType {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (user: AuthUser) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: () => {},
  logout: () => {},
})

export const useAuth = () => useContext(AuthContext)

// ─── Query Client ─────────────────────────────────────────────────────────────
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30_000,
    },
  },
})

// ─── Protected Route ──────────────────────────────────────────────────────────
function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode; allowedRoles?: string[] }) {
  const { isAuthenticated, isLoading, user } = useAuth()
  if (isLoading) return <div className="flex items-center justify-center min-h-screen"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" /></div>
  if (!isAuthenticated) return <Navigate to="/auth" replace />
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    const dashboards: Record<string, string> = { merchant: '/merchant/dashboard', rider: '/rider/dashboard' }
    return <Navigate to={dashboards[user.role] || '/'} replace />
  }
  return <>{children}</>
}

// ─── App ──────────────────────────────────────────────────────────────────────
function App() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showSplash, setShowSplash] = useState(true)

  // Hydrate auth state from server on mount
  useEffect(() => {
    const splashTimer = setTimeout(() => setShowSplash(false), 1800)

    const checkAuth = async () => {
      try {
        const response = await authAPI.me()
        setUser(response.data)
      } catch {
        // Not authenticated — that's fine
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
    return () => clearTimeout(splashTimer)
  }, [])

  const login = (userData: AuthUser) => setUser(userData)
  const logout = async () => {
    try {
      await authAPI.logout()
    } finally {
      setUser(null)
      queryClient.clear()
    }
  }

  if (showSplash) return <SplashScreen />

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      logout,
    }}>
      <ErrorBoundary>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/auth" element={<Auth />} />
              <Route path="/products" element={<Products />} />
              <Route path="/products/:category" element={<Products />} />
              <Route path="/cart" element={<CartPage />} />
              <Route path="/checkout" element={<CheckoutPage />} />
              <Route path="/orders/:id/track" element={<OrderTrackingPage />} />
              <Route path="/payment/success" element={<PaymentSuccessPage />} />
              <Route path="/merchant/register" element={<MerchantRegistrationPage />} />
              <Route path="/driver/register" element={<DriverRegistrationPage />} />
              <Route path="/merchant/dashboard" element={
                <ProtectedRoute allowedRoles={['merchant']}>
                  <MerchantDashboard />
                </ProtectedRoute>
              } />
              <Route path="/rider/dashboard" element={
                <ProtectedRoute allowedRoles={['rider']}>
                  <RiderDashboard />
                </ProtectedRoute>
              } />
              <Route path="/merchant/:id" element={<MerchantPage />} />
              <Route path="/orders" element={<Orders />} />
              <Route path="/orders/:id" element={<Orders />} />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute>
                    <Profile />
                  </ProtectedRoute>
                }
              />
              {/* Rewards & Referral Routes */}
              <Route
                path="/rewards"
                element={
                  <ProtectedRoute>
                    <RewardsDashboard />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/rewards/referral"
                element={
                  <ProtectedRoute>
                    <ReferralPage />
                  </ProtectedRoute>
                }
              />
              {/* 404 - Not Found */}
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </BrowserRouter>
        </QueryClientProvider>
      </ErrorBoundary>
    </AuthContext.Provider>
  )
}

export default App
