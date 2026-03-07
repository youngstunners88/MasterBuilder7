import { useState } from 'react'
import { Bell, ShoppingCart, Menu, X } from 'lucide-react'
import { Link } from 'react-router-dom'

interface HeaderProps {
  showCart?: boolean
  cartCount?: number
}

export function Header({ showCart = false, cartCount = 0 }: HeaderProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <>
      <header className="bg-white shadow-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-sm">
              <svg viewBox="0 0 24 24" className="w-6 h-6 text-secondary-600" fill="currentColor">
                <path d="M12 2C9.5 2 7.5 4 7.5 6.5C7.5 8 8.2 9.3 9.2 10.2L6 16L4 14L2 16L6 20L10 14H14L18 20L22 16L20 14L18 16L14.8 10.2C15.8 9.3 16.5 8 16.5 6.5C16.5 4 14.5 2 12 2ZM12 6C11.4 6 11 5.6 11 5C11 4.4 11.4 4 12 4C12.6 4 13 4.4 13 5C13 5.6 12.6 6 12 6Z"/>
              </svg>
            </div>
            <span className="font-bold text-xl text-secondary-600">iHhashi</span>
          </Link>
          
          {/* Actions */}
          <div className="flex items-center gap-3">
            {showCart && (
              <Link to="/cart" className="relative p-2 hover:bg-gray-100 rounded-full transition-colors">
                <ShoppingCart className="w-5 h-5 text-secondary-500" />
                {cartCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-primary text-secondary-600 text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center">
                    {cartCount}
                  </span>
                )}
              </Link>
            )}
            
            <button className="relative p-2 hover:bg-gray-100 rounded-full transition-colors">
              <Bell className="w-5 h-5 text-secondary-500" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full" />
            </button>
            
            <button 
              onClick={() => setIsMenuOpen(!isMenuOpen)} 
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              {isMenuOpen ? (
                <X className="w-5 h-5 text-secondary-500" />
              ) : (
                <Menu className="w-5 h-5 text-secondary-500" />
              )}
            </button>
          </div>
        </div>
        
        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="bg-white border-t border-gray-100 px-4 py-4 md:hidden animate-slide-down">
            <nav className="space-y-1">
              <Link to="/orders" className="block text-secondary-500 hover:text-secondary-600 hover:bg-gray-50 py-3 px-3 rounded-lg transition-colors">
                My Orders
              </Link>
              <Link to="/profile" className="block text-secondary-500 hover:text-secondary-600 hover:bg-gray-50 py-3 px-3 rounded-lg transition-colors">
                Profile
              </Link>
              <Link to="/rider" className="block text-secondary-500 hover:text-secondary-600 hover:bg-gray-50 py-3 px-3 rounded-lg transition-colors">
                Become a Rider
              </Link>
              <Link to="/merchant-dashboard" className="block text-secondary-500 hover:text-secondary-600 hover:bg-gray-50 py-3 px-3 rounded-lg transition-colors">
                Merchant Portal
              </Link>
              <hr className="my-2 border-gray-100" />
              <Link to="/auth" className="block text-red-500 hover:bg-red-50 py-3 px-3 rounded-lg transition-colors">
                Sign Out
              </Link>
            </nav>
          </div>
        )}
      </header>
    </>
  )
}
