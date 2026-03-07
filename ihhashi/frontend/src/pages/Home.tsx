import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, ShoppingBag, User, Star, Clock, MapPin, Flame, ShoppingCart, Leaf, Home as HomeIcon } from 'lucide-react'
import { useAuth } from '../App'
import ChatBot from '../components/common/ChatBot'

const categories = [
  { id: 'all', name: 'All', icon: Flame },
  { id: 'fastfood', name: 'Fast Food', icon: Flame },
  { id: 'groceries', name: 'Groceries', icon: ShoppingCart },
  { id: 'fresh', name: 'Fresh', icon: Leaf },
]

const popularMerchants = [
  { id: '1', name: 'KFC Rosebank', rating: 4.8, reviews: 234, deliveryTime: '20-30', deliveryFee: 15, image: 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=300&h=200&fit=crop', category: 'Fast Food' },
  { id: '2', name: 'Fresh Market', rating: 4.6, reviews: 189, deliveryTime: '30-45', deliveryFee: 20, image: 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=300&h=200&fit=crop', category: 'Groceries' },
  { id: '3', name: 'Organic Fruits', rating: 4.9, reviews: 156, deliveryTime: '25-35', deliveryFee: 12, image: 'https://images.unsplash.com/photo-1610832958506-4b0ba5a5ee52?w=300&h=200&fit=crop', category: 'Fruits' },
  { id: '4', name: 'Veggie King', rating: 4.7, reviews: 98, deliveryTime: '35-50', deliveryFee: 18, image: 'https://images.unsplash.com/photo-1566385101042-1a0aa0c1268c?w=300&h=200&fit=crop', category: 'Vegetables' },
]

export default function Home() {
  const { isAuthenticated } = useAuth()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState('all')

  return (
    <div className="min-h-screen bg-primary pb-20">
      {/* Yellow Header */}
      <header className="bg-primary sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 pt-4 pb-3">
          {/* Top row: Logo + Location */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              {/* Horse logo */}
              <img src="/images/ihhashi-logo.png" alt="iHhashi" className="w-10 h-10 object-contain" />
              <div>
                <h1 className="font-bold text-xl text-secondary">iHhashi</h1>
                <p className="text-xs text-secondary/70">Delivering to</p>
              </div>
            </div>
            <div className="flex items-center gap-1 text-secondary">
              <MapPin className="w-4 h-4" />
              <span className="text-sm font-medium truncate max-w-[120px]">Soweto, Johannesburg...</span>
            </div>
          </div>
          
          {/* Search Bar */}
          <div className="relative">
            <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-secondary/40" />
            <input
              type="text"
              placeholder="Search food, groceries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 rounded-2xl bg-[#FEF9E7] text-secondary placeholder-secondary/40 focus:outline-none focus:ring-2 focus:ring-secondary/20 shadow-sm"
            />
          </div>
        </div>
      </header>

      {/* Category Pills */}
      <div className="max-w-lg mx-auto px-4 mt-4">
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
          {categories.map((cat) => {
            const Icon = cat.icon
            const isActive = activeCategory === cat.id
            return (
              <button
                key={cat.id}
                onClick={() => setActiveCategory(cat.id)}
                className={`flex items-center gap-2 px-5 py-3 rounded-2xl whitespace-nowrap transition-all ${
                  isActive 
                    ? 'bg-secondary text-primary' 
                    : 'bg-white text-secondary border border-secondary/10'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-primary' : 'text-secondary'}`} />
                <span className="font-medium text-sm">{cat.name}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Promotional Banner */}
      <div className="max-w-lg mx-auto px-4 mt-4">
        <div className="bg-secondary rounded-3xl p-5 shadow-lg">
          <span className="inline-block bg-primary text-secondary text-xs font-bold px-3 py-1 rounded-full mb-3">
            NEW
          </span>
          <h2 className="text-2xl font-bold text-primary mb-2">Empty Fridge?</h2>
          <p className="text-white/90 text-sm mb-1">Full feast! iHhashi delivers</p>
          <p className="text-white/60 text-xs">Free delivery on first order</p>
        </div>
      </div>

      {/* Popular Near You */}
      <div className="max-w-lg mx-auto px-4 mt-6">
        <h3 className="font-bold text-xl text-secondary mb-4">Popular Near You</h3>
        <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-hide -mx-4 px-4">
          {popularMerchants.map((merchant) => (
            <Link
              key={merchant.id}
              to={`/merchant/${merchant.id}`}
              className="min-w-[280px] bg-white rounded-2xl overflow-hidden shadow-md"
            >
              <img 
                src={merchant.image} 
                alt={merchant.name} 
                className="w-full h-32 object-cover" 
              />
              <div className="p-3">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-secondary">{merchant.name}</h4>
                    <p className="text-xs text-secondary/60">{merchant.category}</p>
                  </div>
                  <div className="flex items-center gap-1 bg-primary/20 px-2 py-0.5 rounded-full">
                    <Star className="w-3 h-3 text-primary fill-primary" />
                    <span className="text-xs font-bold text-secondary">{merchant.rating}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 mt-2 text-xs text-secondary/60">
                  <Clock className="w-3 h-3" />
                  <span>{merchant.deliveryTime} min</span>
                  <span>•</span>
                  <span>R{merchant.deliveryFee} delivery</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-secondary/10 py-2 z-50">
        <div className="max-w-lg mx-auto flex justify-around">
          <Link to="/" className="flex flex-col items-center py-1 px-4">
            <HomeIcon className="w-6 h-6 text-secondary fill-secondary" />
            <span className="text-xs mt-1 font-bold text-secondary">Home</span>
          </Link>
          <Link to="/products" className="flex flex-col items-center py-1 px-4">
            <Search className="w-6 h-6 text-secondary/40" />
            <span className="text-xs mt-1 text-secondary/40">Search</span>
          </Link>
          <Link to="/orders" className="flex flex-col items-center py-1 px-4">
            <ShoppingBag className="w-6 h-6 text-secondary/40" />
            <span className="text-xs mt-1 text-secondary/40">Orders</span>
          </Link>
          <Link to={isAuthenticated ? "/profile" : "/auth"} className="flex flex-col items-center py-1 px-4">
            <User className="w-6 h-6 text-secondary/40" />
            <span className="text-xs mt-1 text-secondary/40">Profile</span>
          </Link>
        </div>
      </nav>

      {/* Nduna ChatBot */}
      <ChatBot />
    </div>
  )
}