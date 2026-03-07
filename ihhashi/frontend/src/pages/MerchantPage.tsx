import { ArrowLeft, Star, Clock, MapPin, Plus, Minus, Loader2 } from 'lucide-react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Header } from '../components/Header'
import { merchantsAPI } from '../lib/api'
import { useCart } from '../hooks/useCart'

interface Product {
  id: string
  name: string
  description?: string
  price: number
  category?: string
  image?: string
  image_url?: string
}

interface Merchant {
  id: string
  name: string
  description?: string
  image?: string
  image_url?: string
  rating?: number
  reviews_count?: number
  delivery_time?: string
  distance?: string
}

export function MerchantPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { items, addItem, removeItem, getTotal, getItemCount } = useCart()

  const { data: merchantData, isLoading: merchantLoading } = useQuery({
    queryKey: ['merchant', id],
    queryFn: () => merchantsAPI.get(id!),
    enabled: !!id,
  })

  const { data: productsData, isLoading: productsLoading } = useQuery({
    queryKey: ['merchant-products', id],
    queryFn: () => merchantsAPI.products(id!),
    enabled: !!id,
  })

  const merchant: Merchant | undefined = merchantData?.data
  const products: Product[] = productsData?.data ?? productsData?.data?.products ?? []

  const isLoading = merchantLoading || productsLoading
  const cartCount = getItemCount()
  const cartTotal = getTotal()

  const getQuantity = (productId: string) => {
    const item = items.find(i => i.productId === productId)
    return item?.quantity ?? 0
  }

  const handleAdd = (product: Product) => {
    addItem({
      productId: product.id,
      name: product.name,
      price: product.price,
      quantity: 1,
      image: product.image || product.image_url,
    })
  }

  const handleRemove = (productId: string) => {
    const item = items.find(i => i.productId === productId)
    if (item && item.quantity > 1) {
      // useCart's addItem merges quantities, so we use removeItem and re-add with qty-1
      removeItem(productId)
      addItem({ ...item, quantity: item.quantity - 1 })
    } else {
      removeItem(productId)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#FF6B35]" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <Header showCart cartCount={cartCount} />

      {/* Hero */}
      <div className="relative h-48 bg-primary-500">
        <img
          src={merchant?.image || merchant?.image_url || `https://placehold.co/800x400/FF6B00/white?text=${encodeURIComponent(merchant?.name || 'Shop')}`}
          alt={merchant?.name || 'Merchant'}
          className="w-full h-full object-cover"
        />
        <button onClick={() => navigate(-1)} className="absolute top-4 left-4 bg-white/90 p-2 rounded-full">
          <ArrowLeft className="w-5 h-5" />
        </button>
      </div>

      {/* Info */}
      <div className="bg-white px-4 py-4 border-b">
        <h1 className="text-2xl font-bold text-gray-800">{merchant?.name || 'Shop'}</h1>
        {merchant?.description && <p className="text-gray-500 mt-1">{merchant.description}</p>}

        <div className="flex items-center gap-4 mt-3 text-sm">
          {merchant?.rating != null && (
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 text-yellow-500 fill-current" />
              <span className="font-medium">{merchant.rating}</span>
              {merchant.reviews_count != null && <span className="text-gray-400">({merchant.reviews_count})</span>}
            </div>
          )}
          {merchant?.delivery_time && (
            <div className="flex items-center gap-1 text-gray-600">
              <Clock className="w-4 h-4" />
              <span>{merchant.delivery_time}</span>
            </div>
          )}
          {merchant?.distance && (
            <div className="flex items-center gap-1 text-gray-600">
              <MapPin className="w-4 h-4" />
              <span>{merchant.distance}</span>
            </div>
          )}
        </div>
      </div>

      {/* Menu */}
      <div className="p-4">
        <h2 className="font-semibold text-gray-800 mb-3">Menu</h2>

        {products.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No products available</p>
        ) : (
          <div className="space-y-4">
            {products.map(item => {
              const qty = getQuantity(item.id)
              const imgSrc = item.image || item.image_url || `https://placehold.co/200x200/FF6B00/white?text=${encodeURIComponent(item.name)}`
              return (
                <div key={item.id} className="bg-white rounded-xl p-4 shadow-sm flex gap-4">
                  <img
                    src={imgSrc}
                    alt={item.name}
                    className="w-24 h-24 rounded-lg object-cover"
                  />
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-800">{item.name}</h3>
                    {item.description && <p className="text-sm text-gray-500 mt-1">{item.description}</p>}
                    <div className="flex items-center justify-between mt-3">
                      <span className="font-semibold text-primary-600">R{item.price}</span>

                      {qty > 0 ? (
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => handleRemove(item.id)}
                            className="w-8 h-8 rounded-full border border-primary-500 flex items-center justify-center"
                          >
                            <Minus className="w-4 h-4 text-primary-500" />
                          </button>
                          <span className="font-medium">{qty}</span>
                          <button
                            onClick={() => handleAdd(item)}
                            className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center"
                          >
                            <Plus className="w-4 h-4 text-white" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleAdd(item)}
                          className="bg-primary-500 text-white px-4 py-1.5 rounded-full text-sm font-medium"
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
        )}
      </div>

      {/* Cart Bar */}
      {cartCount > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t p-4 shadow-lg">
          <div className="max-w-4xl mx-auto flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">{cartCount} items</p>
              <p className="font-semibold text-lg">R{cartTotal.toFixed(2)}</p>
            </div>
            <button
              onClick={() => navigate('/cart')}
              className="bg-primary-500 text-white px-6 py-3 rounded-xl font-medium"
            >
              View Cart
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
