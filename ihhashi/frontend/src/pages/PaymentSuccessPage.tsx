import { useEffect, useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { 
  CheckCircle, 
  XCircle, 
  Loader2,
  Download,
  Share2,
  Home,
  ShoppingBag,
  Clock,
  MapPin,
  Phone,
  Receipt,
  ChevronRight,
  UtensilsCrossed,
  Bike
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { ordersAPI, paymentsAPI } from '../lib/api'

interface OrderDetails {
  id: string
  status: string
  total: number
  subtotal: number
  delivery_fee: number
  discount: number
  items: Array<{
    name: string
    quantity: number
    unit_price: number
    total_price: number
  }>
  delivery_address: string
  payment_method: string
  created_at: string
  estimated_delivery?: string
  merchant?: {
    name: string
    phone?: string
  }
}

export function PaymentSuccessPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const orderId = searchParams.get('order_id')
  const method = searchParams.get('method') || 'card'
  const reference = searchParams.get('reference')
  
  const [verificationStatus, setVerificationStatus] = useState<'verifying' | 'success' | 'failed'>('verifying')
  const [errorMessage, setErrorMessage] = useState('')

  // Verify payment if reference is present
  useEffect(() => {
    const verifyPayment = async () => {
      if (reference) {
        try {
          await paymentsAPI.verify(reference)
          setVerificationStatus('success')
        } catch (err: any) {
          setVerificationStatus('failed')
          setErrorMessage(err.message || 'Payment verification failed')
        }
      } else if (orderId) {
        // For cash on delivery or already verified
        setVerificationStatus('success')
      }
    }

    if (reference) {
      verifyPayment()
    } else {
      setVerificationStatus('success')
    }
  }, [reference, orderId])

  // Fetch order details
  const { data: orderData, isLoading: orderLoading } = useQuery({
    queryKey: ['order-payment', orderId],
    queryFn: () => ordersAPI.get(orderId!).then(r => r.data),
    enabled: !!orderId && verificationStatus === 'success',
  })

  const order: OrderDetails | undefined = orderData

  const handleDownloadReceipt = () => {
    // In a real app, this would generate and download a PDF
    alert('Receipt download would start here')
  }

  const handleShare = async () => {
    if (navigator.share && order) {
      try {
        await navigator.share({
          title: `iHhashi Order #${order.id?.slice(-8).toUpperCase()}`,
          text: `I just ordered from iHhashi!`,
          url: window.location.href,
        })
      } catch {
        // User cancelled share
      }
    }
  }

  // Loading state
  if (verificationStatus === 'verifying' || orderLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
        <Loader2 className="w-12 h-12 animate-spin text-[#FF6B35] mb-4" />
        <h2 className="text-xl font-bold text-gray-800">Verifying Payment...</h2>
        <p className="text-gray-500 text-sm mt-2">Please don't close this window</p>
      </div>
    )
  }

  // Error state
  if (verificationStatus === 'failed') {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mb-6">
          <XCircle className="w-10 h-10 text-red-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">Payment Failed</h2>
        <p className="text-gray-500 mb-2 max-w-sm">{errorMessage || 'We couldn\'t process your payment'}</p>
        <div className="space-y-3 w-full max-w-xs mt-6">
          <button 
            onClick={() => navigate('/checkout')}
            className="block w-full bg-[#FF6B35] text-white font-semibold py-3 rounded-xl hover:bg-[#e55a25] transition"
          >
            Try Again
          </button>
          <Link 
            to="/cart" 
            className="block w-full bg-white border border-gray-200 text-gray-700 font-semibold py-3 rounded-xl hover:bg-gray-50 transition"
          >
            Back to Cart
          </Link>
        </div>
      </div>
    )
  }

  // Success state
  return (
    <div className="min-h-screen bg-gray-50 pb-8">
      {/* Success Header */}
      <div className="bg-gradient-to-b from-green-500 to-green-600 text-white pt-12 pb-8 px-6">
        <div className="max-w-lg mx-auto text-center">
          <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-2xl font-bold mb-2">
            {method === 'cash' ? 'Order Confirmed!' : 'Payment Successful!'}
          </h1>
          <p className="text-white/80">
            {method === 'cash' 
              ? 'Your order has been placed successfully' 
              : 'Your payment has been processed successfully'}
          </p>
          
          {order && (
            <div className="mt-4 inline-flex items-center gap-2 bg-white/10 rounded-full px-4 py-2">
              <span className="text-sm">Order #</span>
              <span className="font-bold">{order.id?.slice(-8).toUpperCase()}</span>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 -mt-4">
        {/* Order Status Card */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-[#FF6B35]/10 rounded-full flex items-center justify-center">
                <Clock className="w-6 h-6 text-[#FF6B35]" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Estimated Delivery</p>
                <p className="font-bold text-gray-800">
                  {order?.estimated_delivery 
                    ? new Date(order.estimated_delivery).toLocaleTimeString('en-ZA', { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })
                    : '30-45 mins'}
                </p>
              </div>
            </div>
            <Link 
              to={`/orders/${orderId}`}
              className="flex items-center gap-1 text-[#FF6B35] text-sm font-medium"
            >
              Track
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Status Steps */}
          <div className="flex items-center justify-between">
            <div className="flex flex-col items-center">
              <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center mb-1">
                <CheckCircle className="w-4 h-4 text-white" />
              </div>
              <span className="text-xs text-gray-500">Confirmed</span>
            </div>
            <div className="flex-1 h-0.5 bg-gray-200 mx-2" />
            <div className="flex flex-col items-center">
              <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center mb-1">
                <UtensilsCrossed className="w-4 h-4 text-gray-400" />
              </div>
              <span className="text-xs text-gray-400">Preparing</span>
            </div>
            <div className="flex-1 h-0.5 bg-gray-200 mx-2" />
            <div className="flex flex-col items-center">
              <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center mb-1">
                <Bike className="w-4 h-4 text-gray-400" />
              </div>
              <span className="text-xs text-gray-400">On the way</span>
            </div>
          </div>
        </div>

        {/* Order Summary */}
        {order && (
          <div className="bg-white rounded-xl shadow-sm p-4 mb-4">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Receipt className="w-5 h-5 text-[#FF6B35]" />
              Order Summary
            </h3>
            
            {/* Items */}
            <div className="space-y-2 mb-4">
              {(order.items ?? []).map((item, i) => (
                <div key={i} className="flex justify-between text-sm">
                  <span className="text-gray-600">
                    {item.quantity}× {item.name}
                  </span>
                  <span className="font-medium">R{item.total_price || (item.unit_price * item.quantity)}</span>
                </div>
              ))}
            </div>

            {/* Totals */}
            <div className="border-t border-gray-100 pt-3 space-y-1">
              <div className="flex justify-between text-sm text-gray-500">
                <span>Subtotal</span>
                <span>R{order.subtotal}</span>
              </div>
              <div className="flex justify-between text-sm text-gray-500">
                <span>Delivery Fee</span>
                <span>{order.delivery_fee === 0 ? 'Free' : `R${order.delivery_fee}`}</span>
              </div>
              {order.discount > 0 && (
                <div className="flex justify-between text-sm text-green-600">
                  <span>Discount</span>
                  <span>-R{order.discount}</span>
                </div>
              )}
              <div className="flex justify-between font-bold text-base pt-1">
                <span>Total Paid</span>
                <span className="text-[#FF6B35]">R{order.total}</span>
              </div>
            </div>

            {/* Payment Method */}
            <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between">
              <span className="text-sm text-gray-500">Payment Method</span>
              <span className="text-sm font-medium capitalize">
                {order.payment_method === 'cash' ? 'Cash on Delivery' : order.payment_method}
              </span>
            </div>
          </div>
        )}

        {/* Delivery Address */}
        {order?.delivery_address && (
          <div className="bg-white rounded-xl shadow-sm p-4 mb-4">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-[#FF6B35]" />
              Delivery Address
            </h3>
            <p className="text-sm text-gray-600">{order.delivery_address}</p>
          </div>
        )}

        {/* Merchant Info */}
        {order?.merchant && (
          <div className="bg-white rounded-xl shadow-sm p-4 mb-4">
            <h3 className="font-semibold mb-2">Restaurant</h3>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">{order.merchant.name}</span>
              {order.merchant.phone && (
                <a 
                  href={`tel:${order.merchant.phone}`}
                  className="flex items-center gap-1 text-[#FF6B35] text-sm font-medium"
                >
                  <Phone className="w-4 h-4" />
                  Call
                </a>
              )}
            </div>
          </div>
        )}

        {/* Next Steps */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
          <h3 className="font-medium text-blue-800 mb-2">What's Next?</h3>
          <ul className="text-sm text-blue-600 space-y-1">
            <li>• You'll receive an SMS confirmation shortly</li>
            <li>• Track your order in real-time</li>
            <li>• Rate your experience after delivery</li>
            {method === 'cash' && <li>• Have cash ready for the driver</li>}
          </ul>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <Link 
            to={`/orders/${orderId}`}
            className="block w-full bg-[#FF6B35] text-white font-semibold py-3 rounded-xl text-center hover:bg-[#e55a25] transition"
          >
            Track Your Order
          </Link>
          
          <div className="grid grid-cols-2 gap-3">
            <button 
              onClick={handleDownloadReceipt}
              className="flex items-center justify-center gap-2 bg-white border border-gray-200 text-gray-700 font-semibold py-3 rounded-xl hover:bg-gray-50 transition"
            >
              <Download className="w-4 h-4" />
              Receipt
            </button>
            <button 
              onClick={handleShare}
              className="flex items-center justify-center gap-2 bg-white border border-gray-200 text-gray-700 font-semibold py-3 rounded-xl hover:bg-gray-50 transition"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
          </div>

          <Link 
            to="/products"
            className="flex items-center justify-center gap-2 bg-white border border-gray-200 text-gray-700 font-semibold py-3 rounded-xl hover:bg-gray-50 transition"
          >
            <ShoppingBag className="w-4 h-4" />
            Continue Shopping
          </Link>

          <Link 
            to="/"
            className="flex items-center justify-center gap-2 text-gray-500 font-medium py-2"
          >
            <Home className="w-4 h-4" />
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  )
}
