import { useState, useEffect } from 'react'
import { Search, MapPin } from 'lucide-react'
import { Header } from '../components/Header'
import { CategoryBar } from '../components/CategoryBar'
import { MerchantCard } from '../components/MerchantCard'

const categories = [
  { id: 'all', name: 'All', icon: '🍽️' },
  { id: 'restaurant', name: 'Restaurants', icon: '🍕' },
  { id: 'grocery', name: 'Grocery', icon: '🛒' },
  { id: 'pharmacy', name: 'Pharmacy', icon: '💊' },
  { id: 'retail', name: 'Retail', icon: '🛍️' },
]

const sampleMerchants = [
  {
    id: '1',
    name: 'Kota King',
    category: 'restaurant',
    description: 'Best kotas in Soweto',
    rating: 4.8,
    reviews: 234,
    deliveryTime: '20-30',
    deliveryFee: 15,
    image: 'https://placehold.co/400x200/FF6B00/white?text=Kota+King',
  },
  {
    id: '2',
    name: 'Spaza Express',
    category: 'grocery',
    description: 'Fresh groceries delivered fast',
    rating: 4.5,
    reviews: 156,
    deliveryTime: '30-45',
    deliveryFee: 20,
    image: 'https://placehold.co/400x200/10B981/white?text=Spaza+Express',
  },
  {
    id: '3',
    name: 'Bunny Chow House',
    category: 'restaurant',
    description: 'Authentic Durban bunny chow',
    rating: 4.7,
    reviews: 189,
    deliveryTime: '25-35',
    deliveryFee: 18,
    image: 'https://placehold.co/400x200/F97316/white?text=Bunny+Chow',
  },
]

export function HomePage() {
  const [address, setAddress] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    // Get user location on mount
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (_position) => {
          // Reverse geocode to get address
        },
        (_error) => {
          // Location permission denied or unavailable
        }
      )
    }
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-500 to-primary-600 px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-2">
            Delivery for Mzansi
          </h1>
          <p className="text-primary-100 mb-6">
            Food, groceries, and more - delivered to your door
          </p>
          
          {/* Location Input */}
          <div className="bg-white rounded-xl p-4 shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <MapPin className="w-5 h-5 text-primary-500" />
              <input
                type="text"
                placeholder="Enter delivery address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                className="flex-1 outline-none text-gray-700"
              />
              <button className="text-primary-500 text-sm font-medium">
                Use current location
              </button>
            </div>
            
            {/* Search */}
            <div className="flex items-center gap-3 border-t pt-3">
              <Search className="w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search restaurants, dishes, groceries..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 outline-none text-gray-700"
              />
            </div>
          </div>
        </div>
      </div>
      
      {/* Categories */}
      <div className="bg-white border-b sticky top-0 z-10">
        <CategoryBar 
          categories={categories}
          selected={selectedCategory}
          onSelect={setSelectedCategory}
        />
      </div>
      
      {/* Merchants Grid */}
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">
          {selectedCategory === 'all' ? 'Nearby' : categories.find(c => c.id === selectedCategory)?.name}
        </h2>
        
        <div className="space-y-4">
          {sampleMerchants
            .filter(m => selectedCategory === 'all' || m.category === selectedCategory)
            .map(merchant => (
              <MerchantCard key={merchant.id} merchant={merchant} />
            ))}
        </div>
      </div>
      
      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t flex justify-around py-3 md:hidden">
        <button className="flex flex-col items-center text-primary-500">
          <span className="text-xl">🏠</span>
          <span className="text-xs mt-1">Home</span>
        </button>
        <button className="flex flex-col items-center text-gray-400">
          <span className="text-xl">🔍</span>
          <span className="text-xs mt-1">Search</span>
        </button>
        <button className="flex flex-col items-center text-gray-400">
          <span className="text-xl">📦</span>
          <span className="text-xs mt-1">Orders</span>
        </button>
        <button className="flex flex-col items-center text-gray-400">
          <span className="text-xl">👤</span>
          <span className="text-xs mt-1">Profile</span>
        </button>
      </nav>
    </div>
  )
}
