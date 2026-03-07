/**
 * Custom Hooks
 * Reusable React hooks for the iHhashi app
 */

// Existing hooks
export { useCart } from './useCart';
export { useDebounce } from './useDebounce';
export { useFavorites } from './useFavorites';
export { useMerchant } from './useMerchant';
export { useOrders } from './useOrders';
export { useWebSocket } from './useWebSocket';

// WebSocket hooks
export {
  useOrderTracking,
  useRiderTracking,
  useMerchantNotifications,
  useUserNotifications,
} from './useWebSocket';

export type {
  UseWebSocketOptions,
  UseWebSocketReturn,
  UseOrderTrackingOptions,
  UseOrderTrackingReturn,
  UseRiderTrackingOptions,
  UseRiderTrackingReturn,
  UseMerchantNotificationsOptions,
  UseMerchantNotificationsReturn,
  UseUserNotificationsOptions,
  UseUserNotificationsReturn,
} from './useWebSocket';
