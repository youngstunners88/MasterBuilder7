import { Star, Clock, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'

interface Merchant {
  id: string
  name: string
  category: string
  description: string
  rating: number
  reviews: number
  deliveryTime: string
  deliveryFee: number
  image: string
  distance?: string
}

interface MerchantCardProps {
  merchant: Merchant
  variant?: 'default' | 'compact'
}

export function MerchantCard({ merchant, variant = 'default' }: MerchantCardProps) {
  if (variant === 'compact') {
    return (
      <Link
        to={`/merchant/${merchant.id}`}
        className="block bg-white rounded-2xl shadow-card hover:shadow-card-hover transition-all overflow-hidden group"
      >
        <div className="flex">
          <img
            src={merchant.image}
            alt={merchant.name}
            className="w-24 h-24 object-cover group-hover:scale-105 transition-transform"
          />
          <div className="flex-1 p-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-secondary-600 group-hover:text-secondary-700">{merchant.name}</h3>
                <p className="text-xs text-secondary-400">{merchant.category}</p>
              </div>
              <div className="flex items-center gap-1 bg-primary-100 px-2 py-0.5 rounded-full">
                <Star className="w-3 h-3 text-primary fill-primary" />
                <span className="text-xs font-semibold text-secondary-600">{merchant.rating}</span>
              </div>
            </div>
            <div className="flex items-center gap-3 mt-2 text-xs text-secondary-400">
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>{merchant.deliveryTime} min</span>
              </div>
              <span>•</span>
              <span>R{merchant.deliveryFee} delivery</span>
            </div>
          </div>
        </div>
      </Link>
    )
  }

  return (
    <Link
      to={`/merchant/${merchant.id}`}
      className="block bg-white rounded-2xl shadow-card hover:shadow-card-hover transition-all overflow-hidden group"
    >
      {/* Image */}
      <div className="relative h-40">
        <img
          src={merchant.image}
          alt={merchant.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        <div className="absolute top-3 right-3 bg-secondary-600/90 backdrop-blur-sm text-primary px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {merchant.deliveryTime} min
        </div>
        {merchant.distance && (
          <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-sm text-secondary-600 px-2.5 py-1 rounded-full text-xs font-medium flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {merchant.distance}
          </div>
        )}
      </div>
      
      {/* Info */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-secondary-600 group-hover:text-secondary-700 transition-colors">{merchant.name}</h3>
            <p className="text-sm text-secondary-400 mt-0.5">{merchant.description}</p>
          </div>
          <div className="flex items-center gap-1 bg-primary-100 px-2 py-1 rounded-lg">
            <Star className="w-4 h-4 text-primary fill-primary" />
            <span className="text-sm font-semibold text-secondary-600">{merchant.rating}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-4 mt-3 text-sm text-secondary-400">
          <span className="font-medium text-primary">R{merchant.deliveryFee} delivery</span>
          <span>•</span>
          <span>{merchant.reviews} reviews</span>
        </div>
      </div>
    </Link>
  )
}
