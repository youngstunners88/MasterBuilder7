import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Home, Search, User, ShoppingBag, Clock, ChevronRight } from 'lucide-react'
import ChatBot from '../../components/common/ChatBot'

const mockOrders = [
  { id: '1', status: 'delivered', merchant: 'Kota King', items: '2 items', total: 85, date: 'Today, 14:30' },
  { id: '2', status: 'on_the_way', merchant: 'Soweto Fresh', items: '5 items', total: 142, date: 'Today, 12:15' },
  { id: '3', status: 'preparing', merchant: 'Bunny Chow', items: '1 item', total: 65, date: 'Yesterday' },
]

const statusConfig: Record<string, { label: string; color: string }> = {
  delivered: { label: 'Delivered', color: 'bg-green-500' },
  on_the_way: { label: 'On the way', color: 'bg-secondary' },
  preparing: { label: 'Preparing', color: 'bg-yellow-500' },
}

export default function Orders() {
  const [activeTab, setActiveTab] = useState('active')

  return (
    <div className="min-h-screen bg-primary pb-24">
      {/* Yellow Header */}
      <header className="bg-primary px-4 py-4">
        <div className="flex items-center justify-between">
          <h1 className="font-bold text-2xl text-secondary">My Orders</h1>
          <div className="w-10 h-10 bg-secondary rounded-full flex items-center justify-center">
            <svg width="24" height="24" viewBox="0 0 100 100" fill="none">
              <path d="M20 75C15 70 10 60 15 50C20 40 30 35 35 30C40 25 45 15 50 10C55 5 60 2 65 2C70 2 75 8 75 15C75 22 70 28 65 32C60 36 55 40 52 45C50 50 52 55 55 60C58 65 62 70 62 75C62 82 58 88 52 88C46 88 42 82 38 75C34 68 28 75 20 75Z" fill="white"/>
              <ellipse cx="68" cy="18" rx="4" ry="5" fill="#1A1A1A"/>
            </svg>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => setActiveTab('active')}
            className={`flex-1 py-2 rounded-full font-medium text-sm ${
              activeTab === 'active' ? 'bg-secondary text-primary' : 'bg-white/50 text-secondary'
            }`}
          >
            Active
          </button>
          <button
            onClick={() => setActiveTab('past')}
            className={`flex-1 py-2 rounded-full font-medium text-sm ${
              activeTab === 'past' ? 'bg-secondary text-primary' : 'bg-white/50 text-secondary'
            }`}
          >
            Past Orders
          </button>
        </div>
      </header>

      {/* Orders List */}
      <div className="max-w-lg mx-auto px-4 py-4">
        {mockOrders.map(order => {
          const status = statusConfig[order.status]
          return (
            <Link
              key={order.id}
              to={`/orders/${order.id}`}
              className="bg-secondary/90 text-white rounded-2xl p-4 mb-3 shadow-lg border border-secondary/30 block"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-white">{order.merchant}</h3>
                  <p className="text-sm text-white/70 mt-1">{order.items} • R{order.total}</p>
                  <p className="text-xs text-white/60 mt-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {order.date}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-primary text-secondary">
                    {status.label}
                  </span>
                  <ChevronRight className="w-5 h-5 text-white/70" />
                </div>
              </div>
            </Link>
          )
        })}
      </div>

      {/* Empty State */}
      {mockOrders.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <ShoppingBag className="w-16 h-16 text-secondary/20 mb-4" />
          <p className="text-secondary/60">No orders yet</p>
          <Link to="/" className="mt-4 bg-secondary text-primary px-6 py-2 rounded-full font-medium">
            Start Shopping
          </Link>
        </div>
      )}

      {/* Bottom Navigation */}
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
          <Link to="/orders" className="flex flex-col items-center py-1 px-4">
            <ShoppingBag className="w-6 h-6 text-secondary fill-secondary" />
            <span className="text-xs mt-1 font-bold text-secondary">Orders</span>
          </Link>
          <Link to="/profile" className="flex flex-col items-center py-1 px-4 text-secondary/40">
            <User className="w-6 h-6" />
            <span className="text-xs mt-1">Profile</span>
          </Link>
        </div>
      </nav>

      {/* Nduna ChatBot */}
      <ChatBot />
    </div>
  )
}
