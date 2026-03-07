import { useState, useEffect } from 'react'

type RefundStatus = 'pending' | 'approved' | 'rejected' | 'completed'

interface Refund {
  id: string
  order_id: string
  total_refund_amount: number
  refund_reason: string
  status: RefundStatus
  created_at: string
  deadline?: string
  refund_items: Array<{
    product_name: string
    quantity: number
    total_price: number
  }>
}

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

export function RefundsPage() {
  const [refunds, setRefunds] = useState<Refund[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<RefundStatus | 'all'>('all')

  useEffect(() => {
    fetchRefunds()
  }, [filter])

  const fetchRefunds = async () => {
    setLoading(true)
    try {
      // Mock data for now
      setRefunds([
        {
          id: 'ref-001',
          order_id: 'ord-001',
          total_refund_amount: 85.00,
          refund_reason: 'Item arrived damaged',
          status: 'pending',
          created_at: '2026-03-06T10:00:00Z',
          refund_items: [{ product_name: 'Classic Kota', quantity: 1, total_price: 45 }]
        }
      ])
    } catch (error) {
      console.error('Failed to fetch refunds:', error)
    } finally {
      setLoading(false)
    }
  }

  const statusFilters: { value: RefundStatus | 'all'; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'pending', label: 'Pending' },
    { value: 'approved', label: 'Approved' },
    { value: 'rejected', label: 'Rejected' },
    { value: 'completed', label: 'Completed' },
  ]

  const summary = {
    total: refunds.length,
    pending: refunds.filter(r => r.status === 'pending').length,
    approved: refunds.filter(r => r.status === 'approved' || r.status === 'completed').length,
    rejected: refunds.filter(r => r.status === 'rejected').length,
  }

  return (
    <div className="min-h-screen bg-primary pb-20">
      {/* Yellow Header */}
      <header className="bg-primary px-4 py-6">
        <h1 className="font-bold text-2xl text-secondary">My Refunds</h1>
        <p className="text-sm text-secondary/60 mt-1">Track your refund requests</p>
        
        {/* Summary Cards */}
        <div className="flex gap-3 mt-4">
          <div className="bg-white rounded-xl px-4 py-3 flex-1">
            <p className="text-xl font-bold text-secondary">{summary.total}</p>
            <p className="text-xs text-secondary/60">Total</p>
          </div>
          <div className="bg-white rounded-xl px-4 py-3 flex-1">
            <p className="text-xl font-bold text-yellow-600">{summary.pending}</p>
            <p className="text-xs text-secondary/60">Pending</p>
          </div>
          <div className="bg-white rounded-xl px-4 py-3 flex-1">
            <p className="text-xl font-bold text-green-600">{summary.approved}</p>
            <p className="text-xs text-secondary/60">Approved</p>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto px-4 py-4">
        {/* Filters */}
        <div className="flex gap-2 overflow-x-auto pb-4">
          {statusFilters.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                filter === f.value
                  ? 'bg-secondary text-primary'
                  : 'bg-white text-secondary border border-secondary/10'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Refunds List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-secondary" />
          </div>
        ) : refunds.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center shadow-md">
            <p className="text-secondary/60">No refunds found</p>
          </div>
        ) : (
          <div className="space-y-4">
            {refunds.map((refund) => (
              <div key={refund.id} className="bg-white rounded-2xl p-4 shadow-md">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <p className="text-sm text-secondary/60">Refund #{refund.id.slice(-6)}</p>
                    <p className="text-lg font-bold text-secondary">
                      R{refund.total_refund_amount.toFixed(2)}
                    </p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusColors[refund.status]}`}>
                    {statusLabels[refund.status]}
                  </span>
                </div>
                
                <p className="text-sm text-secondary/80 mb-2">{refund.refund_reason}</p>
                
                {refund.refund_items.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    {refund.refund_items.map((item, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="text-secondary">{item.quantity}x {item.product_name}</span>
                        <span className="font-medium text-secondary">R{item.total_price.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
