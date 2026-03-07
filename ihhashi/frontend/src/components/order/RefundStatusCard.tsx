import type { RefundStatus } from '../../types/order'

interface RefundStatusCardProps {
  refund: {
    id: string
    status: RefundStatus
    total_refund_amount: number
    refund_reason: string
    created_at: string
    deadline?: string
    refund_items: Array<{
      product_name: string
      quantity: number
      total_price: number
    }>
  }
}

export function RefundStatusCard({ refund }: RefundStatusCardProps) {
  const statusColors: Record<RefundStatus, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-green-100 text-green-800',
    rejected: 'bg-red-100 text-red-800',
    completed: 'bg-green-100 text-green-800',
  }

  const statusLabels: Record<RefundStatus, string> = {
    pending: 'Pending',
    approved: 'Approved',
    rejected: 'Rejected',
    completed: 'Completed',
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex justify-between items-start mb-3">
        <div>
          <p className="text-sm text-gray-500">Refund #{refund.id.slice(-6)}</p>
          <p className="text-lg font-bold text-gray-900">
            R{refund.total_refund_amount.toFixed(2)}
          </p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[refund.status]}`}>
          {statusLabels[refund.status]}
        </span>
      </div>
      
      <p className="text-sm text-gray-600 mb-2">{refund.refund_reason}</p>
      
      {refund.refund_items.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-2">Items:</p>
          {refund.refund_items.map((item, idx) => (
            <div key={idx} className="flex justify-between text-sm">
              <span>{item.quantity}x {item.product_name}</span>
              <span>R{item.total_price.toFixed(2)}</span>
            </div>
          ))}
        </div>
      )}
      
      {refund.deadline && (
        <p className="text-xs text-gray-500 mt-3">
          Deadline: {new Date(refund.deadline).toLocaleDateString()}
        </p>
      )}
    </div>
  )
}
