import { useEffect, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, 
  Phone, 
  MessageCircle, 
  MapPin, 
  Clock, 
  CheckCircle2, 
  Package,
  ChefHat,
  Bike,
  Home,
  Loader2,
  AlertCircle,
  Star,
  Copy,
  Share2
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { ordersAPI } from '../lib/api'
import { useAuth } from '../App'

interface OrderStatus {
  status: string
  label: string
  description: string
  icon: any
  color: string
  bgColor: string
}

const orderStatuses: OrderStatus[] = [
  { 
    status: 'pending', 
    label: 'Order Placed', 
    description: 'We\'ve received your order',
    icon: CheckCircle2,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50'
  },
  { 
    status: 'confirmed', 
    label: 'Confirmed', 
    description: 'Restaurant is preparing',
    icon: ChefHat,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50'
  },
  { 
    status: 'preparing', 
    label: 'Preparing', 
    description: 'Your food is being made',
    icon: ChefHat,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50'
  },
  { 
    status: 'ready', 
    label: 'Ready for Pickup', 
    description: 'Waiting for driver',
    icon: Package,
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50'
  },
  { 
    status: 'picked_up', 
    label: 'Picked Up', 
    description: 'Driver has your order',
    icon: Bike,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50'
  },
  { 
    status: 'in_transit', 
    label: 'On the Way', 
    description: 'Heading to you',
    icon: Bike,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50'
  },
  { 
    status: 'delivered', 
    label: 'Delivered', 
    description: 'Enjoy your meal!',
    icon: Home,
    color: 'text-green-600',
    bgColor: 'bg-green-50'
  },
]

export function OrderTrackingPage() {
  const { id: orderId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [copied, setCopied] = useState(false)
  const [showRating, setShowRating] = useState(false)
  const [rating, setRating] = useState(0)

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/auth', { replace: true })
    }
  }, [isAuthenticated, navigate])

  const { data: orderData, isLoading, refetch } = useQuery({
    queryKey: ['order-tracking', orderId],
    queryFn: () => ordersAPI.get(orderId!).then(r => r.data),
    enabled: !!orderId && isAuthenticated,
    refetchInterval: 10_000, // Poll every 10 seconds for live updates
  })

  const order = orderData

  const getCurrentStatusIndex = () => {
    if (!order) return 0
    const index = orderStatuses.findIndex(s => s.status === order.status)
    return index >= 0 ? index : 0
  }

  const currentStatusIndex = getCurrentStatusIndex()
  const isDelivered = order?.status === 'delivered'
  const isActive = !isDelivered && order?.status !== 'cancelled'

  const handleCopyOrderId = () => {
    if (order?.id) {
      navigator.clipboard.writeText(order.id)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleShare = async () => {
    if (navigator.share && order) {
      try {
        await navigator.share({
          title: `iHhashi Order #${order.id?.slice(-8).toUpperCase()}`,
          text: `Track my iHhashi order! Status: ${orderStatuses[currentStatusIndex]?.label}`,
          url: window.location.href,
        })
      } catch {
        // User cancelled share
      }
    }
  }

  const handleSubmitRating = async () => {
    if (rating > 0 && order) {
      try {
        await ordersAPI.rate(order.id, rating)
        setShowRating(false)
        refetch()
      } catch (err) {
        console.error('Failed to submit rating:', err)
      }
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#FF6B35]" />
      </div>
    )
  }

  if (!order) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
        <AlertCircle className="w-12 h-12 text-gray-300 mb-4" />
        <h2 className="text-xl font-bold text-gray-800 mb-2">Order not found</h2>
        <p className="text-gray-500 mb-6">We couldn't find this order</p>
        <Link to="/orders" className="bg-[#FF6B35] text-white font-semibold px-6 py-3 rounded-xl">
          View All Orders
        </Link>
      </div>
    )
  }

  const shortOrderId = order.id?.slice(-8).toUpperCase()

  return (
    <div className="min-h-screen bg-gray-50 pb-8">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center">
            <Link to="/orders" className="p-2 -ml-2">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <div className="ml-2">
              <h1 className="text-lg font-semibold">Order #{shortOrderId}</h1>
              <p className="text-xs text-gray-500">
                {new Date(order.created_at).toLocaleDateString('en-ZA')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button 
              onClick={handleCopyOrderId}
              className="p-2 hover:bg-gray-100 rounded-full transition"
              title="Copy order ID"
            >
              <Copy className={`w-5 h-5 ${copied ? 'text-green-500' : 'text-gray-400'}`} />
            </button>
            <button 
              onClick={handleShare}
              className="p-2 hover:bg-gray-100 rounded-full transition"
              title="Share"
            >
              <Share2 className="w-5 h-5 text-gray-400" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-4 space-y-4">
        {/* Live Status Banner */}
        {isActive && (
          <div className="bg-gradient-to-r from-[#FF6B35] to-orange-500 rounded-xl p-4 text-white">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                {(() => {
                  const StatusIcon = orderStatuses[currentStatusIndex]?.icon || Clock
                  return <StatusIcon className="w-6 h-6" />
                })()}
              </div>
              <div>
                <p className="font-bold text-lg">{orderStatuses[currentStatusIndex]?.label}</p>
                <p className="text-white/80 text-sm">{orderStatuses[currentStatusIndex]?.description}</p>
              </div>
            </div>
            {order.estimated_delivery && (
              <div className="mt-3 pt-3 border-t border-white/20 flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span className="text-sm">
                  Estimated arrival: {new Date(order.estimated_delivery).toLocaleTimeString('en-ZA', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Status Timeline */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h3 className="font-semibold mb-4">Order Status</h3>
          <div className="space-y-0">
            {orderStatuses.slice(0, isDelivered ? undefined : currentStatusIndex + 2).map((status, index) => {
              const isCompleted = index <= currentStatusIndex
              const isCurrent = index === currentStatusIndex
              const StatusIcon = status.icon

              return (
                <div key={status.status} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      isCompleted 
                        ? isCurrent 
                          ? `${status.bgColor} ${status.color}` 
                          : 'bg-green-100 text-green-600'
                        : 'bg-gray-100 text-gray-400'
                    }`}>
                      {isCompleted && !isCurrent ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : (
                        <StatusIcon className="w-5 h-5" />
                      )}
                    </div>
                    {index < orderStatuses.length - 1 && (
                      <div className={`w-0.5 h-8 ${
                        isCompleted && index < currentStatusIndex ? 'bg-green-500' : 'bg-gray-200'
                      }`} />
                    )}
                  </div>
                  <div className={`pb-6 ${isCurrent ? 'opacity-100' : isCompleted ? 'opacity-70' : 'opacity-40'}`}>
                    <p className={`font-medium ${isCurrent ? 'text-gray-900' : 'text-gray-600'}`}>
                      {status.label}
                    </p>
                    <p className="text-sm text-gray-500">{status.description}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Driver Info */}
        {order.rider && isActive && (
          <div className="bg-white rounded-xl shadow-sm p-4">
            <h3 className="font-semibold mb-3">Your Delivery Partner</h3>
            <div className="flex items-center gap-3">
              <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center">
                <span className="text-2xl">🛵</span>
              </div>
              <div className="flex-1">
                <p className="font-medium">{order.rider.name}</p>
                <p className="text-sm text-gray-500">{order.rider.vehicle_type || 'Motorcycle'}</p>
                {order.rider.rating && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <Star className="w-3 h-3 text-yellow-500 fill-yellow-500" />
                    <span className="text-xs text-gray-500">{order.rider.rating}</span>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <a 
                  href={`tel:${order.rider.phone}`}
                  className="w-10 h-10 bg-[#FF6B35] text-white rounded-full flex items-center justify-center hover:bg-[#e55a25] transition"
                >
                  <Phone className="w-5 h-5" />
                </a>
                <button className="w-10 h-10 bg-green-500 text-white rounded-full flex items-center justify-center hover:bg-green-600 transition">
                  <MessageCircle className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Map Placeholder */}
        {isActive && (
          <div className="bg-white rounded-xl shadow-sm overflow-hidden">
            <div className="h-48 bg-gray-100 relative flex items-center justify-center">
              <div className="text-center">
                <MapPin className="w-12 h-12 text-[#FF6B35] mx-auto mb-2" />
                <p className="text-gray-500 text-sm">Live map view</p>
                <p className="text-xs text-gray-400">Driver location updates every 10 seconds</p>
              </div>
              {/* Mock map overlay */}
              <div className="absolute inset-0 bg-gradient-to-br from-gray-50 to-gray-100 opacity-50" />
              <div className="absolute top-4 right-4 bg-white rounded-lg px-3 py-2 shadow-sm">
                <p className="text-xs text-gray-500">Distance</p>
                <p className="font-bold text-[#FF6B35]">2.4 km</p>
              </div>
            </div>
          </div>
        )}

        {/* Order Details */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h3 className="font-semibold mb-3">Order Details</h3>
          <div className="space-y-3">
            {(order.items ?? []).map((item: any, i: number) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-gray-600">
                  {item.quantity}× {item.product_name || item.name}
                </span>
                <span className="font-medium">
                  R{item.total_price || (item.unit_price * item.quantity)}
                </span>
              </div>
            ))}
            <div className="border-t border-gray-100 pt-3 space-y-1">
              <div className="flex justify-between text-sm text-gray-500">
                <span>Subtotal</span>
                <span>R{order.subtotal}</span>
              </div>
              <div className="flex justify-between text-sm text-gray-500">
                <span>Delivery Fee</span>
                <span>R{order.delivery_fee}</span>
              </div>
              {order.discount > 0 && (
                <div className="flex justify-between text-sm text-green-600">
                  <span>Discount</span>
                  <span>-R{order.discount}</span>
                </div>
              )}
              <div className="flex justify-between font-bold text-base pt-1">
                <span>Total</span>
                <span className="text-[#FF6B35]">R{order.total}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Delivery Address */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h3 className="font-semibold mb-2 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-[#FF6B35]" />
            Delivery Address
          </h3>
          <p className="text-sm text-gray-600">
            {order.delivery_address || order.delivery_info?.address_line1}
            {order.delivery_info?.address_line2 && `, ${order.delivery_info.address_line2}`}
            {order.delivery_info?.city && `, ${order.delivery_info.city}`}
          </p>
        </div>

        {/* Rating (shown when delivered) */}
        {isDelivered && !order.rating && (
          <div className="bg-white rounded-xl shadow-sm p-4">
            {!showRating ? (
              <>
                <h3 className="font-semibold mb-2">How was your delivery?</h3>
                <p className="text-sm text-gray-500 mb-3">Rate your experience with this order</p>
                <button
                  onClick={() => setShowRating(true)}
                  className="w-full bg-[#FF6B35] text-white font-medium py-3 rounded-xl hover:bg-[#e55a25] transition"
                >
                  Rate Order
                </button>
              </>
            ) : (
              <>
                <h3 className="font-semibold mb-3">Rate your experience</h3>
                <div className="flex justify-center gap-2 mb-4">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => setRating(star)}
                      className="p-1"
                    >
                      <Star
                        className={`w-8 h-8 ${
                          star <= rating 
                            ? 'text-yellow-500 fill-yellow-500' 
                            : 'text-gray-300'
                        }`}
                      />
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowRating(false)}
                    className="flex-1 py-2 border border-gray-200 rounded-xl font-medium text-gray-600"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmitRating}
                    disabled={rating === 0}
                    className="flex-1 py-2 bg-[#FF6B35] text-white rounded-xl font-medium disabled:opacity-50"
                  >
                    Submit
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* Support */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h3 className="font-semibold mb-3">Need Help?</h3>
          <div className="space-y-2">
            <Link 
              to="/help" 
              className="flex items-center justify-between py-2 text-sm text-gray-600 hover:text-[#FF6B35]"
            >
              <span>Contact Support</span>
              <ArrowLeft className="w-4 h-4 rotate-180" />
            </Link>
            {isActive && (
              <button className="w-full text-left py-2 text-sm text-red-500 hover:text-red-600">
                Cancel Order
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
