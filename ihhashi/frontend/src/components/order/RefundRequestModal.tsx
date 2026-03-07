import { useState } from 'react'
import { RefundReason, RefundItem, REFUND_REASONS } from '../../types/order'

interface OrderItem {
  product_id: string
  product_name: string
  quantity: number
  unit_price: number
  total_price: number
}

interface RefundRequestModalProps {
  orderId: string
  items: OrderItem[]
  onClose: () => void
  onSubmit: (refundData: {
    items: RefundItem[]
    reason: RefundReason
    explanation: string
    evidenceUrls: string[]
  }) => Promise<void>
}

export function RefundRequestModal({ orderId: _orderId, items, onClose, onSubmit }: RefundRequestModalProps) {
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [reason, setReason] = useState<RefundReason | ''>('')
  const [explanation, setExplanation] = useState('')
  const [evidenceUrls, setEvidenceUrls] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [step, setStep] = useState(1)

  const toggleItem = (itemId: string) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId)
    } else {
      newSelected.add(itemId)
    }
    setSelectedItems(newSelected)
  }

  const selectAllItems = () => {
    if (selectedItems.size === items.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(items.map(i => i.product_id)))
    }
  }

  const calculateRefundTotal = () => {
    return items
      .filter(item => selectedItems.has(item.product_id))
      .reduce((sum, item) => sum + item.total_price, 0)
  }

  const handleSubmit = async () => {
    if (!reason || selectedItems.size === 0 || !explanation.trim()) {
      return
    }

    setIsSubmitting(true)
    try {
      const refundItems: RefundItem[] = items
        .filter(item => selectedItems.has(item.product_id))
        .map(item => ({
          product_id: item.product_id,
          reason: reason as RefundReason,
          quantity: item.quantity,
          product_name: item.product_name,
          unit_price: item.unit_price,
          total_price: item.total_price,
        }))

      await onSubmit({
        items: refundItems,
        reason: reason as RefundReason,
        explanation: explanation.trim(),
        evidenceUrls,
      })
      onClose()
    } finally {
      setIsSubmitting(false)
    }
  }

  const canProceedToStep2 = selectedItems.size > 0
  const canSubmit = canProceedToStep2 && reason && explanation.trim().length >= 10

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-lg w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">Request Refund</h2>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded-full transition-colors"
            >
              <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* Progress Steps */}
          <div className="flex items-center mt-4 space-x-2">
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
              step >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
            }`}>
              1
            </div>
            <div className={`flex-1 h-1 rounded ${step >= 2 ? 'bg-blue-600' : 'bg-gray-200'}`} />
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
              step >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
            }`}>
              2
            </div>
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Select Items</span>
            <span>Details</span>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <p className="text-sm text-gray-600">Select items to refund</p>
                <button
                  onClick={selectAllItems}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  {selectedItems.size === items.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>

              <div className="space-y-2">
                {items.map((item) => (
                  <label
                    key={item.product_id}
                    className={`flex items-center p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedItems.has(item.product_id)
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedItems.has(item.product_id)}
                      onChange={() => toggleItem(item.product_id)}
                      className="sr-only"
                    />
                    <div className={`w-5 h-5 rounded border-2 mr-3 flex items-center justify-center ${
                      selectedItems.has(item.product_id)
                        ? 'border-blue-600 bg-blue-600'
                        : 'border-gray-300'
                    }`}>
                      {selectedItems.has(item.product_id) && (
                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{item.product_name}</p>
                      <p className="text-xs text-gray-500">{item.quantity}× R{item.unit_price.toFixed(2)}</p>
                    </div>
                    <p className="text-sm font-semibold text-gray-900">R{item.total_price.toFixed(2)}</p>
                  </label>
                ))}
              </div>

              {selectedItems.size > 0 && (
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Refund Total</span>
                    <span className="font-semibold text-gray-900">R{calculateRefundTotal().toFixed(2)}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              {/* Refund Reason */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason for Refund <span className="text-red-500">*</span>
                </label>
                <select
                  value={reason}
                  onChange={(e) => setReason(e.target.value as RefundReason)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">Select a reason...</option>
                  {REFUND_REASONS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Explanation */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Explanation <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={explanation}
                  onChange={(e) => setExplanation(e.target.value)}
                  placeholder="Please describe why you're requesting a refund (minimum 10 characters)..."
                  rows={4}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                />
                <p className="text-xs text-gray-500 mt-1">
                  {explanation.length}/500 characters (minimum 10)
                </p>
              </div>

              {/* Evidence Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Evidence (Optional)
                </label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    onChange={(e) => {
                      const files = Array.from(e.target.files || [])
                      const urls = files.map(f => URL.createObjectURL(f))
                      setEvidenceUrls([...evidenceUrls, ...urls])
                    }}
                    className="hidden"
                    id="evidence-upload"
                  />
                  <label
                    htmlFor="evidence-upload"
                    className="cursor-pointer"
                  >
                    <svg className="w-8 h-8 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p className="text-sm text-gray-500 mt-2">Click to upload photos</p>
                    <p className="text-xs text-gray-400">PNG, JPG up to 10MB each</p>
                  </label>
                </div>
                
                {evidenceUrls.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {evidenceUrls.map((url, idx) => (
                      <div key={idx} className="relative">
                        <img
                          src={url}
                          alt={`Evidence ${idx + 1}`}
                          className="w-16 h-16 object-cover rounded-lg"
                        />
                        <button
                          onClick={() => setEvidenceUrls(evidenceUrls.filter((_, i) => i !== idx))}
                          className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Summary */}
              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="text-sm font-medium text-blue-900 mb-2">Refund Summary</h4>
                <div className="space-y-1 text-sm text-blue-800">
                  <p><span className="font-medium">Items:</span> {selectedItems.size} selected</p>
                  <p><span className="font-medium">Total:</span> R{calculateRefundTotal().toFixed(2)}</p>
                  <p className="text-xs text-blue-600 mt-2">
                    Refunds are typically processed within 10 business days as per South African Consumer Protection Act.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 flex gap-3">
          {step === 1 ? (
            <>
              <button
                onClick={onClose}
                className="flex-1 py-2 px-4 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!canProceedToStep2}
                className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-2 px-4 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleSubmit}
                disabled={!canSubmit || isSubmitting}
                className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? 'Submitting...' : 'Submit Request'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
