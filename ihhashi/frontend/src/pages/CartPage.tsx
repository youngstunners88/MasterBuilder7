import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Trash2, MapPin, CreditCard, Banknote, Loader2, AlertCircle } from 'lucide-react'
import { useCart } from '../hooks/useCart'
import { useAuth } from '../App'
import { paymentsAPI, ordersAPI } from '../lib/api'

type PaymentMethod = 'cash' | 'card'

export function CartPage() {
  const navigate = useNavigate()
  const { items, removeItem, updateQuantity, clearCart, getTotal, getItemCount } = useCart()
  const { isAuthenticated } = useAuth()

  const [address, setAddress] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('cash')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const subtotal = getTotal()
  const deliveryFee = subtotal > 0 ? 20 : 0
  const total = subtotal + deliveryFee

  const handleCheckout = async () => {
    if (!isAuthenticated) {
      navigate('/auth')
      return
    }
    if (!address.trim()) {
      setError('Please enter a delivery address')
      return
    }
    if (items.length === 0) return

    setLoading(true)
    setError('')

    try {
      // 1. Create the order
      const orderPayload = {
        items: items.map(i => ({ product_id: i.productId, quantity: i.quantity })),
        delivery_address: address,
        payment_method: paymentMethod,
        subtotal,
        delivery_fee: deliveryFee,
        total,
      }
      const orderResp = await ordersAPI.create(orderPayload)
      const orderId: string = orderResp.data.id ?? orderResp.data.order_id

      if (paymentMethod === 'card') {
        // 2a. Initialize Paystack payment
        const payResp = await paymentsAPI.initialize({
          amount: total,
          order_id: orderId,
        })
        const { authorization_url } = payResp.data.data
        // Clear cart before redirect so duplicate orders aren't placed on back-navigation
        clearCart()
        // Redirect to Paystack payment page
        window.location.href = authorization_url
      } else {
        // 2b. Cash on delivery — just confirm
        clearCart()
        navigate(`/orders/${orderId}?new=1`)
      }
    } catch (err: any) {
      setError(err.message || 'Checkout failed. Please try again.')
      setLoading(false)
    }
  }

  if (items.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
        <div className="text-6xl mb-4">🛒</div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">Your cart is empty</h2>
        <p className="text-gray-500 mb-6">Add some items to get started</p>
        <Link to="/products" className="bg-[#FF6B35] text-white font-semibold px-6 py-3 rounded-xl">
          Browse Products
        </Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-32">
      {/* Header */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center">
          <Link to="/products" className="p-2 -ml-2">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <h1 className="text-lg font-semibold ml-2">Cart ({getItemCount()} items)</h1>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-4 space-y-4">
        {/* Items */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          {items.map((item, idx) => (
            <div key={item.productId} className={`flex items-center gap-3 p-4 ${idx < items.length - 1 ? 'border-b border-gray-100' : ''}`}>
              {item.image && (
                <img src={item.image} alt={item.name} className="w-14 h-14 object-cover rounded-lg flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm line-clamp-1">{item.name}</p>
                <p className="text-[#FF6B35] font-bold mt-0.5">R{item.price}</p>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => updateQuantity(item.productId, item.quantity - 1)}
                  className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-lg font-bold hover:bg-gray-200">
                  −
                </button>
                <span className="w-6 text-center font-medium">{item.quantity}</span>
                <button onClick={() => updateQuantity(item.productId, item.quantity + 1)}
                  className="w-8 h-8 rounded-full bg-[#FF6B35] text-white flex items-center justify-center text-lg font-bold hover:bg-[#e55a25]">
                  +
                </button>
                <button onClick={() => removeItem(item.productId)}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-red-500 ml-1">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Delivery Address */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="w-5 h-5 text-[#FF6B35]" />
            <h3 className="font-semibold">Delivery Address</h3>
          </div>
          <textarea
            placeholder="Enter your full delivery address&#10;e.g. 123 Main Street, Soweto, Johannesburg, 1804"
            value={address}
            onChange={(e) => { setAddress(e.target.value); setError('') }}
            rows={3}
            className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20 resize-none"
          />
        </div>

        {/* Payment Method */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h3 className="font-semibold mb-3">Payment Method</h3>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setPaymentMethod('cash')}
              className={`flex items-center gap-2 p-3 rounded-xl border-2 transition ${paymentMethod === 'cash' ? 'border-[#FF6B35] bg-orange-50' : 'border-gray-200'}`}
            >
              <Banknote className={`w-5 h-5 ${paymentMethod === 'cash' ? 'text-[#FF6B35]' : 'text-gray-400'}`} />
              <span className={`text-sm font-medium ${paymentMethod === 'cash' ? 'text-[#FF6B35]' : 'text-gray-600'}`}>Cash on Delivery</span>
            </button>
            <button
              onClick={() => setPaymentMethod('card')}
              className={`flex items-center gap-2 p-3 rounded-xl border-2 transition ${paymentMethod === 'card' ? 'border-[#FF6B35] bg-orange-50' : 'border-gray-200'}`}
            >
              <CreditCard className={`w-5 h-5 ${paymentMethod === 'card' ? 'text-[#FF6B35]' : 'text-gray-400'}`} />
              <span className={`text-sm font-medium ${paymentMethod === 'card' ? 'text-[#FF6B35]' : 'text-gray-600'}`}>Card (Paystack)</span>
            </button>
          </div>
        </div>

        {/* Order Summary */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h3 className="font-semibold mb-3">Order Summary</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between text-gray-600">
              <span>Subtotal ({getItemCount()} items)</span>
              <span>R{subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Delivery fee</span>
              <span>R{deliveryFee.toFixed(2)}</span>
            </div>
            <div className="border-t border-gray-100 pt-2 flex justify-between font-bold text-base">
              <span>Total</span>
              <span className="text-[#FF6B35]">R{total.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-center gap-2 text-red-700 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* Checkout Footer */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 p-4">
        <div className="max-w-lg mx-auto">
          <button
            onClick={handleCheckout}
            disabled={loading || items.length === 0}
            className="w-full bg-[#FF6B35] text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 disabled:opacity-60 hover:bg-[#e55a25] transition"
          >
            {loading ? (
              <><Loader2 className="w-5 h-5 animate-spin" /> Processing...</>
            ) : (
              <>
                {isAuthenticated
                  ? `Place Order · R${total.toFixed(2)}`
                  : 'Sign in to checkout'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
