import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Home, Search, UtensilsCrossed } from 'lucide-react'

export function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center">
          <button onClick={() => navigate(-1)} className="p-2 -ml-2">
            <ArrowLeft className="w-6 h-6" />
          </button>
          <h1 className="text-lg font-semibold ml-2">Page Not Found</h1>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        {/* 404 Illustration */}
        <div className="relative mb-8">
          <div className="w-40 h-40 bg-[#FF6B35]/10 rounded-full flex items-center justify-center">
            <div className="w-32 h-32 bg-[#FF6B35]/20 rounded-full flex items-center justify-center">
              <UtensilsCrossed className="w-16 h-16 text-[#FF6B35]" />
            </div>
          </div>
          <div className="absolute -bottom-2 -right-2 w-16 h-16 bg-white rounded-full flex items-center justify-center shadow-lg">
            <span className="text-2xl font-bold text-[#FF6B35]">404</span>
          </div>
        </div>

        {/* Message */}
        <h2 className="text-2xl font-bold text-gray-800 mb-3">
          Oops! Page not found
        </h2>
        <p className="text-gray-500 max-w-sm mb-8">
          The page you're looking for doesn't exist or has been moved. 
          Let's get you back on track.
        </p>

        {/* Quick Links */}
        <div className="w-full max-w-xs space-y-3">
          <Link 
            to="/"
            className="flex items-center justify-center gap-2 w-full bg-[#FF6B35] text-white font-semibold py-3 rounded-xl hover:bg-[#e55a25] transition"
          >
            <Home className="w-5 h-5" />
            Back to Home
          </Link>
          
          <Link 
            to="/products"
            className="flex items-center justify-center gap-2 w-full bg-white border border-gray-200 text-gray-700 font-semibold py-3 rounded-xl hover:bg-gray-50 transition"
          >
            <Search className="w-5 h-5" />
            Browse Food
          </Link>

          <button 
            onClick={() => navigate(-1)}
            className="flex items-center justify-center gap-2 w-full bg-white text-gray-500 font-medium py-3 hover:text-gray-700 transition"
          >
            <ArrowLeft className="w-5 h-5" />
            Go Back
          </button>
        </div>

        {/* Help Section */}
        <div className="mt-12 pt-8 border-t border-gray-200 w-full max-w-xs">
          <p className="text-sm text-gray-500 mb-3">Need help?</p>
          <div className="flex justify-center gap-4">
            <Link to="/help" className="text-[#FF6B35] text-sm font-medium hover:underline">
              Help Center
            </Link>
            <span className="text-gray-300">|</span>
            <a href="mailto:support@ihhashi.com" className="text-[#FF6B35] text-sm font-medium hover:underline">
              Contact Support
            </a>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 py-4">
        <div className="max-w-lg mx-auto px-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="w-8 h-8 bg-[#FF6B35] rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">H</span>
            </div>
            <span className="font-bold text-lg text-gray-800">iHhashi</span>
          </div>
          <p className="text-xs text-gray-400">
            Fast delivery across Mzansi
          </p>
        </div>
      </footer>
    </div>
  )
}
