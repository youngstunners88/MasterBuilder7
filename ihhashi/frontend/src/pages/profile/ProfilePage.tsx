import { } from 'react'
import { Link } from 'react-router-dom'
import { Home, Search, User, ShoppingBag, MapPin, CreditCard, HelpCircle, LogOut, ChevronRight, Bell } from 'lucide-react'
import { useAuth } from '../../App'
import ChatBot from '../../components/common/ChatBot'

export default function ProfilePage() {
  const { user, isAuthenticated, logout } = useAuth()

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-primary flex flex-col items-center justify-center p-6">
        <div className="w-20 h-20 bg-secondary rounded-full flex items-center justify-center mb-6">
          <svg width="40" height="40" viewBox="0 0 100 100" fill="none">
            <path d="M20 75C15 70 10 60 15 50C20 40 30 35 35 30C40 25 45 15 50 10C55 5 60 2 65 2C70 2 75 8 75 15C75 22 70 28 65 32C60 36 55 40 52 45C50 50 52 55 55 60C58 65 62 70 62 75C62 82 58 88 52 88C46 88 42 82 38 75C34 68 28 75 20 75Z" fill="white"/>
            <ellipse cx="68" cy="18" rx="4" ry="5" fill="#1A1A1A"/>
          </svg>
        </div>
        <h1 className="font-bold text-2xl text-secondary mb-2">Sign in to iHhashi</h1>
        <p className="text-secondary/60 text-center mb-6">Access your orders, saved addresses, and more</p>
        <Link to="/auth" className="bg-secondary text-primary px-8 py-3 rounded-full font-bold w-full max-w-xs text-center">
          Sign In / Register
        </Link>
      </div>
    )
  }

  const menuItems = [
    { icon: MapPin, label: 'Saved Addresses', to: '/addresses' },
    { icon: CreditCard, label: 'Payment Methods', to: '/payment-methods' },
    { icon: Bell, label: 'Notifications', to: '/notifications' },
    { icon: HelpCircle, label: 'Help & Support', to: '/help' },
  ]

  return (
    <div className="min-h-screen bg-primary text-white pb-24">
      <header className="bg-primary px-4 py-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center border-2 border-white/40">
            <img src="/images/ihhashi-logo.png" alt="iHhashi" className="w-10 h-10 object-contain" />
          </div>
          <div>
            <h1 className="font-bold text-2xl text-secondary">{user?.full_name || 'User'}</h1>
            <p className="text-sm text-secondary/70">{user?.phone || '+27 xx xxx xxxx'}</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-5 text-center">
          <div className="bg-secondary/80 rounded-2xl py-3">
            <p className="text-2xl font-bold">12</p>
            <p className="text-xs text-white/70">Orders</p>
          </div>
          <div className="bg-secondary/80 rounded-2xl py-3">
            <p className="text-2xl font-bold">3</p>
            <p className="text-xs text-white/70">Saved Addresses</p>
          </div>
          <div className="bg-secondary/80 rounded-2xl py-3">
            <p className="text-2xl font-bold">4.8</p>
            <p className="text-xs text-white/70">Rating</p>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-4 space-y-3">
        {menuItems.map((item, idx) => {
          const Icon = item.icon
          return (
            <Link
              key={idx}
              to={item.to}
              className="bg-secondary/80 rounded-2xl p-4 flex items-center justify-between shadow-lg border border-secondary/30"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary/30 rounded-full flex items-center justify-center">
                  <Icon className="w-5 h-5 text-secondary" />
                </div>
                <span className="font-medium">{item.label}</span>
              </div>
              <ChevronRight className="w-5 h-5 text-white/60" />
            </Link>
          )
        })}

        <button
          onClick={logout}
          className="bg-secondary p-4 rounded-2xl w-full flex items-center justify-between border border-white/20 shadow-lg mt-2"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <LogOut className="w-5 h-5 text-white" />
            </div>
            <span className="font-medium">Logout</span>
          </div>
          <ChevronRight className="w-5 h-5 text-white/60" />
        </button>
      </div>

      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-secondary/10 py-2 z-50">
        <div className="max-w-lg mx-auto flex justify-around">
          <Link to="/" className="flex flex-col items-center py-1 px-4 text-secondary/40">
            <Home className="w-6 h-6" />
            <span className="text-xs mt-1">Home</span>
          </Link>
          <Link to="/products" className="flex flex-col items-center py-1 px-4 text-secondary/40">
            <Search className="w-6 h-6" />
            <span className="text-xs mt-1">Search</span>
          </Link>
          <Link to="/orders" className="flex flex-col items-center py-1 px-4 text-secondary/40">
            <ShoppingBag className="w-6 h-6" />
            <span className="text-xs mt-1">Orders</span>
          </Link>
          <Link to="/profile" className="flex flex-col items-center py-1 px-4">
            <User className="w-6 h-6 text-secondary fill-secondary" />
            <span className="text-xs mt-1 font-bold text-secondary">Profile</span>
          </Link>
        </div>
      </nav>

      <ChatBot />
    </div>
  )
}
