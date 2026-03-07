// Refund types only - OrderStatus is defined in websocket.ts
export type RefundStatus = 
  | 'pending' 
  | 'approved' 
  | 'rejected' 
  | 'completed'

export type RefundReason = 
  | 'damaged'
  | 'wrong_item'
  | 'missing_item'
  | 'quality_issue'
  | 'not_as_described'
  | 'other'

export interface RefundItem {
  product_id: string
  quantity: number
  reason: RefundReason
  order_item_id?: string
  product_name?: string
  unit_price?: number
  total_price?: number
  refund_reason?: RefundReason
}

export const REFUND_REASONS: { value: RefundReason; label: string }[] = [
  { value: 'damaged', label: 'Item arrived damaged' },
  { value: 'wrong_item', label: 'Wrong item delivered' },
  { value: 'missing_item', label: 'Item missing from order' },
  { value: 'quality_issue', label: 'Quality not as expected' },
  { value: 'not_as_described', label: 'Item not as described' },
  { value: 'other', label: 'Other reason' },
]
