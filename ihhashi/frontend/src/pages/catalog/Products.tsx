import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Search, ShoppingCart, Plus, Minus, Home, User, ShoppingBag } from 'lucide-react'
import { useCart } from '../../hooks/useCart'
import ChatBot from '../../components/common/ChatBot'

const mockProducts = [
  { id: '1', name: 'Classic Kota', price: 45, category: 'fastfood', stock: 50, image: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=300&h=200&fit=crop' },
  { id: '2', name: 'Fresh Apples 1kg', price: 35, category: 'fresh', stock: 100, image: 'https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=300&h=200&fit=crop' },
  { id: '3', name: 'Bunny Chow', price: 65, category: 'fastfood', stock: 30, image: 'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=300&h=200&fit=crop' },
  { id: '4', name: 'Spinach Bunch', price: 25, category: 'fresh', stock: 25, image: 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=300&h=200&fit=crop' },
  { id: '5', name: 'Gatsby Sandwich', price: 75, category: 'fastfood', stock: 75, image: 'https://images.unsplash.com/photo-1551782450-a2132b4ba21d?w=300&h=200&fit=crop' },
  { id: '6', name: 'Carrots 1kg', price: 20, category: 'fresh', stock: 40, image: 'https://images.unsplash.com/photo-1445282768818-728615cc910a?w=300&h=200&fit=crop' },
]

const categories = ['All', 'Fast Food', 'Fresh', 'Groceries']

export default function Products() {
  const { category } = useParams()
  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState(category || 'All')
  const { items, addItem, updateQuantity } = useCart()

  const filteredProducts = mockProducts.filter(p => {
    const matchesCategory = activeCategory === 'All' || p.category.toLowerCase() === activeCategory.toLowerCase()
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  const getItemQuantity = (productId: string) => {
    const item = items.find(i => i.productId === productId)
    return item?.quantity || 0
  }

  return (
    <div className="min-h-screen bg-primary pb-24">
      {/* Yellow Header */}
      <header className="bg-primary sticky top-0 z-10">
        <div className="px-4 py-3 flex items-center gap-3">
          <Link to="/" className="p-2 -ml-2 text-secondary">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <div className="flex-1 relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-secondary/40" />
            <input
              type="text"
              placeholder="Search food, groceries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-3 rounded-2xl bg-white text-secondary placeholder-secondary/40 focus:outline-none focus:ring-2 focus:ring-secondary/20"
            />
          </div>
          <Link to="/cart" className="relative text-secondary">
            <ShoppingCart className="w-6 h-6" />
            {items.length > 0 && (
              <span className="absolute -top-1 -right-1 bg-secondary text-primary text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
                {items.length}
              </span>
            )}
          </Link>
        </div>

        {/* Category Tabs */}
        <div className="px-4 py-2 flex gap-2 overflow-x-auto scrollbar-hide">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-4 py-2 rounded-full text-sm whitespace-nowrap font-medium transition-all ${
                activeCategory === cat
                  ? 'bg-secondary text-primary'
                  : 'bg-white/50 text-secondary border border-secondary/10'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </header>

      {/* Product Grid */}
      <div className="max-w-lg mx-auto px-4 py-4">
        <h2 className="font-bold text-xl text-secondary mb-4">Products</h2>
        <div className="grid grid-cols-2 gap-3">
          {filteredProducts.map(product => {
            const qty = getItemQuantity(product.id)
            return (
              <div key={product.id} className="bg-secondary/80 text-white rounded-2xl overflow-hidden shadow-md border border-secondary/20">
                <img src={product.image} alt={product.name} className="w-full h-32 object-cover" />
                <div className="p-3">
                  <h4 className="font-bold text-sm text-white line-clamp-2">{product.name}</h4>
                  <p className="text-xs text-white/70 mt-1">{product.stock} in stock</p>
                  <div className="flex justify-between items-center mt-2">
                    <span className="font-bold text-primary">R{product.price}</span>
                    {qty > 0 ? (
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateQuantity(product.id, qty - 1)}
                          className="w-7 h-7 rounded-full bg-primary/80 flex items-center justify-center shadow-inner"
                        >
                          <Minus className="w-4 h-4 text-secondary" />
                        </button>
                        <span className="font-medium">{qty}</span>
                        <button
                          onClick={() => updateQuantity(product.id, qty + 1)}
                          className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center"
                        >
                          <Plus className="w-4 h-4 text-white" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => addItem({
                          productId: product.id,
                          name: product.name,
                          price: product.price,
                          quantity: 1,
                          image: product.image
                        })}
                        className="bg-primary text-secondary text-xs px-3 py-1.5 rounded-full font-semibold shadow-lg"
                      >
                        Add
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-secondary/10 py-2 z-50">
        <div className="max-w-lg mx-auto flex justify-around">
          <Link to="/" className="flex flex-col items-center py-1 px-4 text-secondary/40">
            <Home className="w-6 h-6" />
            <span className="text-xs mt-1">Home</span>
          </Link>
          <Link to="/products" className="flex flex-col items-center py-1 px-4">
            <Search className="w-6 h-6 text-secondary fill-secondary" />
            <span className="text-xs mt-1 font-bold text-secondary">Search</span>
          </Link>
          <Link to="/orders" className="flex flex-col items-center py-1 px-4 text-secondary/40">
            <ShoppingBag className="w-6 h-6" />
            <span className="text-xs mt-1">Orders</span>
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
