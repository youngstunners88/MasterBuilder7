import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  ArrowLeft, 
  MapPin, 
  CreditCard, 
  Banknote, 
  Loader2, 
  AlertCircle,
  Ticket,
  Clock,
  Shield,
  ChevronRight,
  Home,
  Building2
} from 'lucide-react'
import { useCart } from '../hooks/useCart'
import { useAuth } from '../App'
import { paymentsAPI, ordersAPI, addressesAPI } from '../lib/api'
import { useQuery } from '@tanstack/react-query'

type PaymentMethod = 'cash' | 'card' | 'yoco'
type AddressType = 'home' | 'work' | 'other'

interface SavedAddress {
  id: string
  label: string
  address: string
  lat: number
  lng: number
  is_default?: boolean
}

export function CheckoutPage() {
  const navigate = useNavigate()
  const { items, clearCart, getTotal, getItemCount } = useCart()
  const { isAuthenticated, user } = useAuth()

  const [selectedAddressId, setSelectedAddressId] = useState<string>('')
  const [newAddress, setNewAddress] = useState('')
  const [addressType, setAddressType] = useState<AddressType>('home')
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('card')
  const [promoCode, setPromoCode] = useState('')
  const [appliedPromo, setAppliedPromo] = useState<{ code: string; discount: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showNewAddressForm, setShowNewAddressForm] = useState(false)

  // Fetch saved addresses
  const { data: addressesData } = useQuery({
    queryKey: ['addresses'],
    queryFn: () => addressesAPI.list().then(r => r.data),
    enabled: isAuthenticated,
  })

  const savedAddresses: SavedAddress[] = addressesData?.addresses ?? []

  // Calculate totals
  const subtotal = getTotal()
  const deliveryFee = subtotal > 0 ? (subtotal > 200 ? 0 : 25) : 0
  const discount = appliedPromo?.discount ?? 0
  const total = Math.max(0, subtotal + deliveryFee - discount)

  const handleApplyPromo = () => {
    if (!promoCode.trim()) return
    // Mock promo codes for demo
    const promos: Record<string, number> = {
      'WELCOME20': 20,
      'IHASHI10': 10,
      'FREEDEL': deliveryFee,
    }
    const discount = promos[promoCode.toUpperCase()]
    if (discount) {
      setAppliedPromo({ code: promoCode.toUpperCase(), discount })
      setPromoCode('')
    } else {
      setError('Invalid promo code')
    }
  }

  const handleRemovePromo = () => {
    setAppliedPromo(null)
  }

  const handleCheckout = async () => {
    if (!isAuthenticated) {
      navigate('/auth')
      return
    }

    const deliveryAddress = selectedAddressId 
      ? savedAddresses.find(a => a.id === selectedAddressId)?.address
      : newAddress

    if (!deliveryAddress?.trim()) {
      setError('Please select or enter a delivery address')
      return
    }
    if (items.length === 0) return

    setLoading(true)
    setError('')

    try {
      // 1. Create the order
      const orderPayload = {
        items: items.map(i => ({ product_id: i.productId, quantity: i.quantity })),
        delivery_address: deliveryAddress,
        payment_method: paymentMethod,
        subtotal,
        delivery_fee: deliveryFee,
        discount,
        total,
        promo_code: appliedPromo?.code,
      }
      const orderResp = await ordersAPI.create(orderPayload)
      const orderId: string = orderResp.data.id ?? orderResp.data.order_id

      if (paymentMethod === 'card' || paymentMethod === 'yoco') {
        // 2a. Initialize payment
        const payResp = await paymentsAPI.initialize({
          amount: total,
          order_id: orderId,
          email: user?.email,
        })
        const { authorization_url } = payResp.data.data
        clearCart()
        window.location.href = authorization_url
      } else {
        // 2b. Cash on delivery
        clearCart()
        navigate(`/payment/success?order_id=${orderId}&method=cash`)
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
          <Link to="/cart" className="p-2 -ml-2">
            <ArrowLeft className="w-6 h-6" />
          </Link>
          <h1 className="text-lg font-semibold ml-2">Checkout</h1>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-4 space-y-4">
        {/* Cart Summary */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold flex items-center gap-2">
              <span className="w-8 h-8 bg-[#FF6B35]/10 rounded-full flex items-center justify-center">
                <span className="text-[#FF6B35] font-bold text-sm">{getItemCount()}</span>
              </span>
              Items in Cart
            </h3>
            <Link to="/cart" className="text-[#FF6B35] text-sm font-medium">Edit</Link>
          </div>
          <div className="space-y-2">
            {items.slice(0, 3).map((item) => (
              <div key={item.productId} className="flex justify-between text-sm">
                <span className="text-gray-600">{item.quantity}× {item.name}</span>
                <span className="font-medium">R{(item.price * item.quantity).toFixed(2)}</span>
              </div>
            ))}
            {items.length > 3 && (
              <p className="text-sm text-gray-400">+{items.length - 3} more items</p>
            )}
          </div>
        </div>

        {/* Delivery Address */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center gap-2 mb-3">
            <MapPin className="w-5 h-5 text-[#FF6B35]" />
            <h3 className="font-semibold">Delivery Address</h3>
          </div>

          {/* Saved Addresses */}
          {savedAddresses.length > 0 && !showNewAddressForm && (
            <div className="space-y-2 mb-3">
              {savedAddresses.map((addr) => (
                <button
                  key={addr.id}
                  onClick={() => setSelectedAddressId(addr.id)}
                  className={`w-full flex items-start gap-3 p-3 rounded-xl border-2 transition text-left ${
                    selectedAddressId === addr.id 
                      ? 'border-[#FF6B35] bg-orange-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className={`mt-0.5 ${selectedAddressId === addr.id ? 'text-[#FF6B35]' : 'text-gray-400'}`}>
                    {addr.label.toLowerCase().includes('work') ? <Building2 className="w-5 h-5" /> : <Home className="w-5 h-5" />}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{addr.label}</span>
                      {addr.is_default && (
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">Default</span>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">{addr.address}</p>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* New Address Form */}
          {showNewAddressForm ? (
            <div className="space-y-3">
              <textarea
                placeholder="Enter your full delivery address&#10;e.g. 123 Main Street, Soweto, Johannesburg, 1804"
                value={newAddress}
                onChange={(e) => { setNewAddress(e.target.value); setError('') }}
                rows={3}
                className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20 resize-none"
              />
              <div className="flex gap-2">
                {(['home', 'work', 'other'] as AddressType[]).map((type) => (
                  <button
                    key={type}
                    onClick={() => setAddressType(type)}
                    className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium capitalize transition ${
                      addressType === type
                        ? 'bg-[#FF6B35] text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setShowNewAddressForm(false)}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowNewAddressForm(true)}
              className="w-full py-3 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 font-medium text-sm hover:border-[#FF6B35] hover:text-[#FF6B35] transition flex items-center justify-center gap-2"
            >
              <MapPin className="w-4 h-4" />
              Add New Address
            </button>
          )}
        </div>

        {/* Payment Method */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <h3 className="font-semibold mb-3">Payment Method</h3>
          <div className="space-y-2">
            <button
              onClick={() => setPaymentMethod('card')}
              className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition ${
                paymentMethod === 'card' ? 'border-[#FF6B35] bg-orange-50' : 'border-gray-200'
              }`}
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                paymentMethod === 'card' ? 'bg-[#FF6B35] text-white' : 'bg-gray-100 text-gray-500'
              }`}>
                <CreditCard className="w-5 h-5" />
              </div>
              <div className="flex-1 text-left">
                <p className={`font-medium ${paymentMethod === 'card' ? 'text-[#FF6B35]' : 'text-gray-700'}`}>
                  Card Payment
                </p>
                <p className="text-xs text-gray-500">Paystack (Visa, Mastercard)</p>
              </div>
              {paymentMethod === 'card' && <div className="w-5 h-5 rounded-full bg-[#FF6B35] flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-white" />
              </div>}
            </button>

            <button
              onClick={() => setPaymentMethod('yoco')}
              className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition ${
                paymentMethod === 'yoco' ? 'border-[#FF6B35] bg-orange-50' : 'border-gray-200'
              }`}
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                paymentMethod === 'yoco' ? 'bg-[#FF6B35] text-white' : 'bg-gray-100 text-gray-500'
              }`}>
                <CreditCard className="w-5 h-5" />
              </div>
              <div className="flex-1 text-left">
                <p className={`font-medium ${paymentMethod === 'yoco' ? 'text-[#FF6B35]' : 'text-gray-700'}`}>
                  Yoco
                </p>
                <p className="text-xs text-gray-500">South African payment gateway</p>
              </div>
              {paymentMethod === 'yoco' && <div className="w-5 h-5 rounded-full bg-[#FF6B35] flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-white" />
              </div>}
            </button>

            <button
              onClick={() => setPaymentMethod('cash')}
              className={`w-full flex items-center gap-3 p-3 rounded-xl border-2 transition ${
                paymentMethod === 'cash' ? 'border-[#FF6B35] bg-orange-50' : 'border-gray-200'
              }`}
            >
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                paymentMethod === 'cash' ? 'bg-[#FF6B35] text-white' : 'bg-gray-100 text-gray-500'
              }`}>
                <Banknote className="w-5 h-5" />
              </div>
              <div className="flex-1 text-left">
                <p className={`font-medium ${paymentMethod === 'cash' ? 'text-[#FF6B35]' : 'text-gray-700'}`}>
                  Cash on Delivery
                </p>
                <p className="text-xs text-gray-500">Pay when you receive</p>
              </div>
              {paymentMethod === 'cash' && <div className="w-5 h-5 rounded-full bg-[#FF6B35] flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-white" />
              </div>}
            </button>
          </div>
        </div>

        {/* Promo Code */}
        <div className="bg-white rounded-xl shadow-sm p-4">
          <div className="flex items-center gap-2 mb-3">
            <Ticket className="w-5 h-5 text-[#FF6B35]" />
            <h3 className="font-semibold">Promo Code</h3>
          </div>
          
          {appliedPromo ? (
            <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded-xl px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-green-600 font-medium">{appliedPromo.code}</span>
                <span className="text-green-600 text-sm">-R{appliedPromo.discount}</span>
              </div>
              <button onClick={handleRemovePromo} className="text-red-500 text-sm font-medium">
                Remove
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Enter promo code"
                value={promoCode}
                onChange={(e) => setPromoCode(e.target.value)}
                className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-sm outline-none focus:border-[#FF6B35] focus:ring-2 focus:ring-[#FF6B35]/20 uppercase"
              />
              <button
                onClick={handleApplyPromo}
                disabled={!promoCode.trim()}
                className="px-4 py-3 bg-gray-100 text-gray-700 font-medium rounded-xl disabled:opacity-50 hover:bg-gray-200 transition"
              >
                Apply
              </button>
            </div>
          )}
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
              <span className="flex items-center gap-1">
                Delivery fee
                {deliveryFee === 0 && <span className="text-green-600 text-xs">(Free)</span>}
              </span>
              <span>{deliveryFee === 0 ? 'R0.00' : `R${deliveryFee.toFixed(2)}`}</span>
            </div>
            {discount > 0 && (
              <div className="flex justify-between text-green-600">
                <span>Discount</span>
                <span>-R{discount.toFixed(2)}</span>
              </div>
            )}
            <div className="border-t border-gray-100 pt-2 flex justify-between font-bold text-base">
              <span>Total</span>
              <span className="text-[#FF6B35]">R{total.toFixed(2)}</span>
            </div>
          </div>
          
          {/* Delivery Time Estimate */}
          <div className="mt-4 flex items-center gap-2 text-sm text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
            <Clock className="w-4 h-4" />
            <span>Estimated delivery: 30-45 minutes</span>
          </div>
        </div>

        {/* Security Note */}
        <div className="flex items-center gap-2 text-xs text-gray-400 justify-center">
          <Shield className="w-4 h-4" />
          <span>Secure checkout powered by Paystack & Yoco</span>
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
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-xs text-gray-500">Total Amount</p>
              <p className="text-xl font-bold text-[#FF6B35]">R{total.toFixed(2)}</p>
            </div>
            <button
              onClick={handleCheckout}
              disabled={loading || items.length === 0}
              className="bg-[#FF6B35] text-white font-bold py-3 px-8 rounded-xl flex items-center gap-2 disabled:opacity-60 hover:bg-[#e55a25] transition"
            >
              {loading ? (
                <><Loader2 className="w-5 h-5 animate-spin" /> Processing...</>
              ) : (
                <>
                  Place Order
                  <ChevronRight className="w-5 h-5" />
                </>
              )}
            </button>
          </div>
          {!isAuthenticated && (
            <p className="text-xs text-center text-gray-500">
              You'll be asked to sign in before completing your order
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
