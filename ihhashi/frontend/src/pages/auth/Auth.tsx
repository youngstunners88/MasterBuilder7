import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { ArrowLeft, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../../App'
import { authAPI } from '../../lib/api'

export default function Auth() {
  const navigate = useNavigate()
  const { isAuthenticated, login } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const [form, setForm] = useState({
    email: '',
    phone: '',
    full_name: '',
    password: '',
  })

  // Already logged in → redirect home
  if (isAuthenticated) return <Navigate to="/" replace />

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    setError('')
  }

  const handleLogin = async () => {
    if (!form.email || !form.password) {
      setError('Please fill in all fields')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await authAPI.login({ email: form.email, password: form.password })
      const { user, access_token, refresh_token } = response.data
      // Store tokens in memory via the API lib (not localStorage for security)
      // The api.ts interceptor handles cookie-based auth, but we also store token in memory
      localStorage.setItem('access_token', access_token)
      if (refresh_token) localStorage.setItem('refresh_token', refresh_token)
      login(user)
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async () => {
    if (!form.email || !form.phone || !form.password || !form.full_name) {
      setError('Please fill in all fields')
      return
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    setError('')
    try {
      await authAPI.register({
        email: form.email,
        phone: form.phone,
        name: form.full_name,
        password: form.password,
        role: 'customer',
      })
      // Auto-login after registration
      const loginResp = await authAPI.login({ email: form.email, password: form.password })
      const { user, access_token, refresh_token } = loginResp.data
      localStorage.setItem('access_token', access_token)
      if (refresh_token) localStorage.setItem('refresh_token', refresh_token)
      login(user)
      navigate('/')
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <div className="px-4 py-3 flex items-center border-b border-gray-100">
        <button onClick={() => navigate(-1)} className="p-2 -ml-2">
          <ArrowLeft className="w-6 h-6" />
        </button>
        <h1 className="text-lg font-semibold ml-2">{mode === 'login' ? 'Sign In' : 'Create Account'}</h1>
      </div>

      <div className="max-w-md mx-auto px-6 py-8">
        <h2 className="text-2xl font-bold mb-1">
          {mode === 'login' ? 'Welcome back' : 'Join iHhashi'}
        </h2>
        <p className="text-gray-500 mb-8 text-sm">
          {mode === 'login' ? 'Sign in to your account' : 'Fast delivery across Mzansi'}
        </p>

        <div className="space-y-4">
          {mode === 'register' && (
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Full Name</label>
              <input
                name="full_name"
                type="text"
                placeholder="Thandi Nkosi"
                value={form.full_name}
                onChange={handleChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
              />
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Email</label>
            <input
              name="email"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={handleChange}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
            />
          </div>

          {mode === 'register' && (
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Phone Number</label>
              <div className="flex items-center border border-gray-200 rounded-xl overflow-hidden focus-within:border-[#FF6B35] focus-within:ring-2 focus-within:ring-[#FF6B35]/20">
                <span className="px-3 py-3 bg-gray-50 text-gray-600 font-medium border-r border-gray-200">+27</span>
                <input
                  name="phone"
                  type="tel"
                  placeholder="821234567"
                  value={form.phone.replace(/^\+27|^0/, '')}
                  onChange={(e) => setForm(p => ({ ...p, phone: `+27${e.target.value.replace(/\D/g, '')}` }))}
                  className="flex-1 px-3 py-3 outline-none"
                  maxLength={10}
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-gray-700 block mb-1">Password</label>
            <div className="relative">
              <input
                name="password"
                type={showPassword ? 'text' : 'password'}
                placeholder={mode === 'register' ? 'Min 8 chars, 1 uppercase, 1 number' : 'Your password'}
                value={form.password}
                onChange={handleChange}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 pr-12 outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20"
              />
              <button
                type="button"
                onClick={() => setShowPassword(p => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-xl">
              {error}
            </div>
          )}

          <button
            onClick={mode === 'login' ? handleLogin : handleRegister}
            disabled={loading}
            className="w-full bg-[#FF6B35] text-white font-semibold py-3.5 rounded-xl disabled:opacity-60 flex items-center justify-center gap-2"
          >
            {loading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
            {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>

          <div className="text-center pt-2">
            {mode === 'login' ? (
              <p className="text-sm text-gray-500">
                Don't have an account?{' '}
                <button onClick={() => { setMode('register'); setError('') }} className="text-[#FF6B35] font-medium">
                  Sign up
                </button>
              </p>
            ) : (
              <p className="text-sm text-gray-500">
                Already have an account?{' '}
                <button onClick={() => { setMode('login'); setError('') }} className="text-[#FF6B35] font-medium">
                  Sign in
                </button>
              </p>
            )}
          </div>
        </div>

        <p className="text-xs text-gray-400 text-center mt-8">
          By continuing, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  )
}
