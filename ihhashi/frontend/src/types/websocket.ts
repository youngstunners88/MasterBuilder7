/**
 * WebSocket Event Types
 * Matches the backend WebSocketEventType enum
 */
export enum WebSocketEventType {
  // Order Events
  ORDER_CREATED = 'order_created',
  ORDER_STATUS_UPDATED = 'order_status_updated',
  ORDER_ASSIGNED = 'order_assigned',
  ORDER_CANCELLED = 'order_cancelled',

  // Driver Events
  DRIVER_LOCATION_UPDATE = 'driver_location_update',
  DRIVER_STATUS_UPDATE = 'driver_status_update',
  DRIVER_ASSIGNED = 'driver_assigned',

  // Delivery Events
  DELIVERY_COMPLETED = 'delivery_completed',
  DELIVERY_FAILED = 'delivery_failed',
  ESTIMATED_ARRIVAL = 'estimated_arrival',

  // Messaging Events
  NEW_MESSAGE = 'new_message',
  MESSAGE_READ = 'message_read',

  // System Events
  PING = 'ping',
  PONG = 'pong',
  HEARTBEAT = 'heartbeat',
  AUTHENTICATED = 'authenticated',
  ERROR = 'error',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',

  // Client Events
  SUBSCRIBE = 'subscribe',
  UNSUBSCRIBE = 'unsubscribe',
  SUBSCRIBED = 'subscribed',
  UNSUBSCRIBED = 'unsubscribed',
  GET_LOCATION = 'get_location',
  GET_STATUS = 'get_status',
}

/**
 * Room Types
 */
export enum RoomType {
  ORDER = 'order',
  DRIVER = 'driver',
  MERCHANT = 'merchant',
  USER = 'user',
  ADMIN = 'admin',
}

/**
 * Order Status
 */
export enum OrderStatus {
  PENDING = 'pending',
  CONFIRMED = 'confirmed',
  PREPARING = 'preparing',
  READY = 'ready',
  PICKED_UP = 'picked_up',
  IN_TRANSIT = 'in_transit',
  DELIVERED = 'delivered',
  CANCELLED = 'cancelled',
}

/**
 * Driver Status
 */
export enum DriverStatus {
  OFFLINE = 'offline',
  AVAILABLE = 'available',
  BUSY = 'busy',
  BREAK = 'break',
}

/**
 * Base WebSocket Message
 */
export interface WebSocketMessage {
  type: WebSocketEventType | string;
  timestamp?: string;
  [key: string]: any;
}

/**
 * Location Data
 */
export interface LocationData {
  latitude: number;
  longitude: number;
  heading?: number;
  speed?: number;
  last_updated?: string;
}

/**
 * Order Created Event
 */
export interface OrderCreatedEvent extends WebSocketMessage {
  type: WebSocketEventType.ORDER_CREATED;
  order_id: string;
  order: {
    id: string;
    buyer_id: string;
    store_id: string;
    items: Array<{
      product_id: string;
      product_name: string;
      quantity: number;
      unit_price: number;
      total_price: number;
    }>;
    subtotal: number;
    delivery_fee: number;
    total: number;
    status: OrderStatus;
    delivery_info: {
      address_label: string;
      address_line1: string;
      address_line2?: string;
      city: string;
      area?: string;
      latitude?: number;
      longitude?: number;
      recipient_phone?: string;
      delivery_instructions?: string;
    };
    created_at: string;
  };
}

/**
 * Order Status Updated Event
 */
export interface OrderStatusUpdatedEvent extends WebSocketMessage {
  type: WebSocketEventType.ORDER_STATUS_UPDATED;
  order_id: string;
  status: OrderStatus;
  status_history?: Array<{
    status: OrderStatus;
    timestamp: string;
    actor?: string;
  }>;
}

/**
 * Driver Location Update Event
 */
export interface DriverLocationUpdateEvent extends WebSocketMessage {
  type: WebSocketEventType.DRIVER_LOCATION_UPDATE;
  order_id?: string;
  rider_id?: string;
  rider_location: LocationData;
}

/**
 * Driver Assigned Event
 */
export interface DriverAssignedEvent extends WebSocketMessage {
  type: WebSocketEventType.DRIVER_ASSIGNED;
  order_id: string;
  rider_id: string;
  rider_name?: string;
  rider_phone?: string;
  rider_location?: LocationData;
}

/**
 * Delivery Completed Event
 */
export interface DeliveryCompletedEvent extends WebSocketMessage {
  type: WebSocketEventType.DELIVERY_COMPLETED;
  order_id: string;
  rider_id?: string;
  message?: string;
}

/**
 * New Message Event
 */
export interface NewMessageEvent extends WebSocketMessage {
  type: WebSocketEventType.NEW_MESSAGE;
  sender_id: string;
  order_id?: string;
  message: string;
}

/**
 * Connected Event
 */
export interface ConnectedEvent extends WebSocketMessage {
  type: WebSocketEventType.CONNECTED;
  room_type?: RoomType;
  room_id?: string;
  message?: string;
  user_id?: string;
  role?: string;
}

/**
 * Authenticated Event
 */
export interface AuthenticatedEvent extends WebSocketMessage {
  type: WebSocketEventType.AUTHENTICATED;
  user_id: string;
  role: string;
}

/**
 * Error Event
 */
export interface ErrorEvent extends WebSocketMessage {
  type: WebSocketEventType.ERROR;
  message: string;
  code?: number;
}

/**
 * Heartbeat/Pong Event
 */
export interface HeartbeatEvent extends WebSocketMessage {
  type: WebSocketEventType.HEARTBEAT | WebSocketEventType.PONG;
}

/**
 * Subscribe/Unsubscribe Events
 */
export interface SubscribeEvent extends WebSocketMessage {
  type: WebSocketEventType.SUBSCRIBE | WebSocketEventType.UNSUBSCRIBE;
  room_type: RoomType;
  room_id: string;
  is_owner?: boolean;
}

/**
 * Union type for all WebSocket events
 */
export type WebSocketEvent =
  | OrderCreatedEvent
  | OrderStatusUpdatedEvent
  | DriverLocationUpdateEvent
  | DriverAssignedEvent
  | DeliveryCompletedEvent
  | NewMessageEvent
  | ConnectedEvent
  | AuthenticatedEvent
  | ErrorEvent
  | HeartbeatEvent
  | SubscribeEvent
  | WebSocketMessage;

/**
 * WebSocket Connection Status
 */
export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

/**
 * WebSocket Options
 */
export interface WebSocketOptions {
  autoReconnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (event: WebSocketEvent) => void;
}

/**
 * Order with real-time updates
 */
export interface OrderWithRealtime {
  id: string;
  buyer_id: string;
  store_id: string;
  rider_id?: string;
  items: Array<{
    product_id: string;
    product_name: string;
    quantity: number;
    unit_price: number;
    total_price: number;
  }>;
  subtotal: number;
  delivery_fee: number;
  total: number;
  status: OrderStatus;
  status_history: Array<{
    status: OrderStatus;
    timestamp: string;
    actor?: string;
  }>;
  delivery_info: {
    address_label: string;
    address_line1: string;
    address_line2?: string;
    city: string;
    area?: string;
    latitude?: number;
    longitude?: number;
    recipient_phone?: string;
    delivery_instructions?: string;
  };
  created_at: string;
  confirmed_at?: string;
  delivered_at?: string;
  estimated_delivery?: string;
  payment_method: string;
  payment_status: string;
  rider_location?: LocationData;
  rider_name?: string;
  rider_phone?: string;
}

/**
 * Notification types for toast messages
 */
export enum NotificationType {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
}

/**
 * Notification data
 */
export interface NotificationData {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: number;
  orderId?: string;
  autoDismiss?: boolean;
  dismissAfter?: number;
}
