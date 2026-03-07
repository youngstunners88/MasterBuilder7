import { useState } from 'react'
import { OrderStatus } from '../../types/websocket'

interface OrderItem {
  product_id: string
  product_name: string
  quantity: number
  unit_price: number
  total_price: number
}

interface DeliveryInfo {
  address_label: string
  address_line1: string
  address_line2?: string
  city: string
  area?: string
  recipient_phone: string
}

interface Order {
  id: string
  buyer_id: string
  store_id: string
  rider_id?: string
  items: OrderItem[]
  subtotal: number
  delivery_fee: number
  total: number
  currency: string
  status: OrderStatus
  delivery_info: DeliveryInfo
  created_at: string
  delivered_at?: string
  payment_method: string
  payment_status: string
  buyer_notes?: string
}

interface OrderCardProps {
  order: Order
  onRequestRefund?: (orderId: string) => void
  onTrackOrder?: (orderId: string) => void
}

const statusColors: Record<OrderStatus, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-blue-100 text-blue-800',
  preparing: 'bg-indigo-100 text-indigo-800',
  ready: 'bg-purple-100 text-purple-800',
  picked_up: 'bg-cyan-100 text-cyan-800',
  in_transit: 'bg-teal-100 text-teal-800',
  delivered: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
}

const statusLabels: Record<OrderStatus, string> = {
  pending: 'Pending',
  confirmed: 'Confirmed',
  preparing: 'Preparing',
  ready: 'Ready for Pickup',
  picked_up: 'Picked Up',
  in_transit: 'On the Way',
  delivered: 'Delivered',
  cancelled: 'Cancelled',
}

export function OrderCard({ order, onRequestRefund, onTrackOrder }: OrderCardProps) {
  const [expanded, setExpanded] = useState(false)

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-ZA', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const canRequestRefund = order.status === 'delivered' && order.payment_status !== 'refunded'
  const canTrack = ['confirmed', 'preparing', 'ready', 'picked_up', 'in_transit'].includes(order.status)

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div 
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex justify-between items-start">
          <div>
            <p className="text-sm text-gray-500">Order #{order.id.slice(-8).toUpperCase()}</p>
            <p className="text-xs text-gray-400 mt-1">{formatDate(order.created_at)}</p>
          </div>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[order.status]}`}>
            {statusLabels[order.status]}
          </span>
        </div>
        
        <div className="mt-3 flex justify-between items-center">
          <div className="text-sm text-gray-600">
            {order.items.length} item{order.items.length !== 1 ? 's' : ''}
          </div>
          <div className="text-right">
            <p className="font-semibold text-gray-900">R{order.total.toFixed(2)}</p>
            <p className="text-xs text-gray-400">{order.payment_method}</p>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-gray-100 p-4 space-y-4">
          {/* Items */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Items</h4>
            <div className="space-y-2">
              {order.items.map((item, idx) => (
                <div key={idx} className="flex justify-between text-sm">
                  <span className="text-gray-600">
                    {item.quantity}× {item.product_name}
                  </span>
                  <span className="text-gray-900">R{item.total_price.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Delivery Address */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-1">Delivery Address</h4>
            <p className="text-sm text-gray-600">
              {order.delivery_info.address_line1}
              {order.delivery_info.address_line2 && `, ${order.delivery_info.address_line2}`}
            </p>
            <p className="text-sm text-gray-600">
              {order.delivery_info.city}
              {order.delivery_info.area && `, ${order.delivery_info.area}`}
            </p>
          </div>

          {/* Price Breakdown */}
          <div className="pt-2 border-t border-gray-100">
            <div className="flex justify-between text-sm text-gray-600">
              <span>Subtotal</span>
              <span>R{order.subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm text-gray-600 mt-1">
              <span>Delivery</span>
              <span>R{order.delivery_fee.toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-semibold mt-2">
              <span>Total</span>
              <span>R{order.total.toFixed(2)}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            {canTrack && onTrackOrder && (
              <button
                onClick={() => onTrackOrder(order.id)}
                className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                Track Order
              </button>
            )}
            {canRequestRefund && onRequestRefund && (
              <button
                onClick={() => onRequestRefund(order.id)}
                className="flex-1 py-2 px-4 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200 transition-colors"
              >
                Request Refund
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
