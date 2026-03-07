/**
 * useWebSocket Hook
 * React hook for WebSocket connections with automatic reconnection
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import {
  WebSocketEvent,
  WebSocketEventType,
  ConnectionStatus,
  WebSocketOptions,
  OrderStatus,
  LocationData,
  RoomType,
  OrderWithRealtime,
  NotificationData,
  NotificationType,
} from '../types/websocket';
import { websocketService } from '../services/websocket';

/**
 * Options for useWebSocket hook
 */
export interface UseWebSocketOptions extends WebSocketOptions {
  autoConnect?: boolean;
  endpoint?: string;
}

/**
 * Return type for useWebSocket hook
 */
export interface UseWebSocketReturn {
  // Connection state
  status: ConnectionStatus;
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;

  // Actions
  connect: () => Promise<void>;
  disconnect: () => void;
  send: (message: Partial<WebSocketEvent>) => boolean;
  subscribe: (roomType: RoomType, roomId: string, isOwner?: boolean) => void;
  unsubscribe: (roomType: RoomType, roomId: string) => void;

  // Event registration
  on: (type: string, handler: (event: WebSocketEvent) => void) => () => void;
  off: (type: string, handler: (event: WebSocketEvent) => void) => void;
}

/**
 * Hook for general WebSocket connection
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = false, endpoint = '/ws', ...wsOptions } = options;
  
  const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
  const [error, setError] = useState<Error | null>(null);
  const handlersRef = useRef<Array<{ type: string; handler: (event: WebSocketEvent) => void }>>([]);

  const isConnected = status === ConnectionStatus.CONNECTED;
  const isConnecting = status === ConnectionStatus.CONNECTING || status === ConnectionStatus.RECONNECTING;

  const connect = useCallback(async () => {
    setError(null);
    
    try {
      await websocketService.connect(endpoint, {
        ...wsOptions,
        onConnect: () => {
          setStatus(ConnectionStatus.CONNECTED);
          wsOptions.onConnect?.();
        },
        onDisconnect: () => {
          setStatus(ConnectionStatus.DISCONNECTED);
          wsOptions.onDisconnect?.();
        },
        onError: (err) => {
          setStatus(ConnectionStatus.ERROR);
          setError(err instanceof Error ? err : new Error('WebSocket error'));
          wsOptions.onError?.(err);
        },
        onMessage: wsOptions.onMessage,
      });
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to connect'));
      throw err;
    }
  }, [endpoint, wsOptions]);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setStatus(ConnectionStatus.DISCONNECTED);
  }, []);

  const send = useCallback((message: Partial<WebSocketEvent>): boolean => {
    return websocketService.send(message);
  }, []);

  const subscribe = useCallback((roomType: RoomType, roomId: string, isOwner: boolean = false) => {
    websocketService.subscribe(roomType, roomId, isOwner);
  }, []);

  const unsubscribe = useCallback((roomType: RoomType, roomId: string) => {
    websocketService.unsubscribe(roomType, roomId);
  }, []);

  const on = useCallback((type: string, handler: (event: WebSocketEvent) => void): (() => void) => {
    handlersRef.current.push({ type, handler });
    return websocketService.on(type, handler);
  }, []);

  const off = useCallback((type: string, handler: (event: WebSocketEvent) => void) => {
    handlersRef.current = handlersRef.current.filter(
      (h) => h.type !== type || h.handler !== handler
    );
    websocketService.off(type, handler);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      // Only disconnect if we're the only component using the service
      // This is a simplification - in production, you'd want reference counting
      handlersRef.current.forEach(({ type, handler }) => {
        websocketService.off(type, handler);
      });
    };
  }, [autoConnect, connect]);

  return {
    status,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    send,
    subscribe,
    unsubscribe,
    on,
    off,
  };
}

/**
 * Hook for tracking a specific order
 */
export interface UseOrderTrackingOptions {
  orderId: string;
  onStatusUpdate?: (status: OrderStatus, event: WebSocketEvent) => void;
  onLocationUpdate?: (location: LocationData, event: WebSocketEvent) => void;
  onDriverAssigned?: (driverId: string, event: WebSocketEvent) => void;
  onDeliveryComplete?: (event: WebSocketEvent) => void;
  onError?: (error: Error) => void;
}

export interface UseOrderTrackingReturn {
  order: OrderWithRealtime | null;
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  requestLocation: () => void;
  requestStatus: () => void;
}

export function useOrderTracking(options: UseOrderTrackingOptions): UseOrderTrackingReturn {
  const { 
    orderId, 
    onStatusUpdate, 
    onLocationUpdate, 
    onDriverAssigned,
    onDeliveryComplete,
    onError,
  } = options;

  const [order, setOrder] = useState<OrderWithRealtime | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const connect = useCallback(async () => {
    if (!orderId) return;
    
    setIsConnecting(true);
    setError(null);

    try {
      await websocketService.trackOrder(orderId, (event) => {
        switch (event.type) {
          case WebSocketEventType.CONNECTED:
            setIsConnected(true);
            setIsConnecting(false);
            if (event.order) {
              setOrder((prev) => ({ ...prev, ...event.order } as OrderWithRealtime));
            }
            break;

          case WebSocketEventType.ORDER_STATUS_UPDATED:
            setOrder((prev) => 
              prev ? { ...prev, status: event.status, status_history: event.status_history || [] } : null
            );
            onStatusUpdate?.(event.status, event);
            break;

          case WebSocketEventType.DRIVER_LOCATION_UPDATE:
            if (event.rider_location) {
              setOrder((prev) =>
                prev ? { ...prev, rider_location: event.rider_location! } : null
              );
              onLocationUpdate?.(event.rider_location, event);
            }
            break;

          case WebSocketEventType.DRIVER_ASSIGNED:
            setOrder((prev) =>
              prev ? { 
                ...prev, 
                rider_id: event.rider_id,
                rider_name: event.rider_name,
                rider_phone: event.rider_phone,
                rider_location: event.rider_location,
              } : null
            );
            onDriverAssigned?.(event.rider_id!, event);
            break;

          case WebSocketEventType.DELIVERY_COMPLETED:
            setOrder((prev) =>
              prev ? { ...prev, status: OrderStatus.DELIVERED } : null
            );
            onDeliveryComplete?.(event);
            break;

          case WebSocketEventType.ERROR:
            setError(new Error(event.message || 'WebSocket error'));
            onError?.(new Error(event.message || 'WebSocket error'));
            break;
        }
      });
    } catch (err) {
      setIsConnecting(false);
      setError(err instanceof Error ? err : new Error('Failed to connect'));
      onError?.(err instanceof Error ? err : new Error('Failed to connect'));
    }
  }, [orderId, onStatusUpdate, onLocationUpdate, onDriverAssigned, onDeliveryComplete, onError]);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setIsConnected(false);
    setOrder(null);
  }, []);

  const requestLocation = useCallback(() => {
    websocketService.requestLocation();
  }, []);

  const requestStatus = useCallback(() => {
    websocketService.requestStatus();
  }, []);

  // Auto-connect when orderId changes
  useEffect(() => {
    if (orderId) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [orderId]);

  return {
    order,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    requestLocation,
    requestStatus,
  };
}

/**
 * Hook for rider location updates
 */
export interface UseRiderTrackingOptions {
  riderId: string;
  onOrderAssigned?: (orderId: string, event: WebSocketEvent) => void;
  onMessage?: (event: WebSocketEvent) => void;
  onError?: (error: Error) => void;
}

export interface UseRiderTrackingReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  updateLocation: (location: LocationData) => void;
  updateStatus: (status: 'available' | 'busy' | 'offline' | 'break') => void;
  acceptOrder: (orderId: string) => void;
  completeDelivery: (orderId: string) => void;
  sendMessage: (orderId: string, message: string) => void;
}

export function useRiderTracking(options: UseRiderTrackingOptions): UseRiderTrackingReturn {
  const { riderId, onOrderAssigned, onMessage, onError } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const connect = useCallback(async () => {
    if (!riderId) return;

    setIsConnecting(true);
    setError(null);

    try {
      await websocketService.connectAsRider(
        riderId,
        (event) => {
          if (event.order_id) {
            onOrderAssigned?.(event.order_id, event);
          }
        },
        (event) => {
          if (event.type === WebSocketEventType.CONNECTED) {
            setIsConnected(true);
            setIsConnecting(false);
          } else if (event.type === WebSocketEventType.ERROR) {
            setError(new Error(event.message || 'WebSocket error'));
            onError?.(new Error(event.message || 'WebSocket error'));
          }
          onMessage?.(event);
        }
      );
    } catch (err) {
      setIsConnecting(false);
      setError(err instanceof Error ? err : new Error('Failed to connect'));
      onError?.(err instanceof Error ? err : new Error('Failed to connect'));
    }
  }, [riderId, onOrderAssigned, onMessage, onError]);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setIsConnected(false);
  }, []);

  const updateLocation = useCallback((location: LocationData) => {
    websocketService.updateLocation(location);
  }, []);

  const updateStatus = useCallback((status: 'available' | 'busy' | 'offline' | 'break') => {
    websocketService.updateStatus(status);
  }, []);

  const acceptOrder = useCallback((orderId: string) => {
    websocketService.acceptOrder(orderId);
  }, []);

  const completeDelivery = useCallback((orderId: string) => {
    websocketService.completeDelivery(orderId);
  }, []);

  const sendMessage = useCallback((orderId: string, message: string) => {
    websocketService.sendMessage(orderId, message);
  }, []);

  // Auto-connect when riderId changes
  useEffect(() => {
    if (riderId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [riderId]);

  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    updateLocation,
    updateStatus,
    acceptOrder,
    completeDelivery,
    sendMessage,
  };
}

/**
 * Hook for merchant notifications
 */
export interface UseMerchantNotificationsOptions {
  merchantId: string;
  onNewOrder?: (order: any, event: WebSocketEvent) => void;
  onMessage?: (event: WebSocketEvent) => void;
  onError?: (error: Error) => void;
}

export interface UseMerchantNotificationsReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  updateOrderStatus: (orderId: string, status: OrderStatus) => void;
}

export function useMerchantNotifications(options: UseMerchantNotificationsOptions): UseMerchantNotificationsReturn {
  const { merchantId, onNewOrder, onMessage, onError } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const connect = useCallback(async () => {
    if (!merchantId) return;

    setIsConnecting(true);
    setError(null);

    try {
      await websocketService.connectAsMerchant(
        merchantId,
        (event) => {
          if (event.order) {
            onNewOrder?.(event.order, event);
          }
        },
        (event) => {
          if (event.type === WebSocketEventType.CONNECTED) {
            setIsConnected(true);
            setIsConnecting(false);
          } else if (event.type === WebSocketEventType.ERROR) {
            setError(new Error(event.message || 'WebSocket error'));
            onError?.(new Error(event.message || 'WebSocket error'));
          }
          onMessage?.(event);
        }
      );
    } catch (err) {
      setIsConnecting(false);
      setError(err instanceof Error ? err : new Error('Failed to connect'));
      onError?.(err instanceof Error ? err : new Error('Failed to connect'));
    }
  }, [merchantId, onNewOrder, onMessage, onError]);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setIsConnected(false);
  }, []);

  const updateOrderStatus = useCallback((orderId: string, status: OrderStatus) => {
    websocketService.updateOrderStatus(orderId, status);
  }, []);

  // Auto-connect when merchantId changes
  useEffect(() => {
    if (merchantId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [merchantId]);

  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    updateOrderStatus,
  };
}

/**
 * Hook for user notifications
 */
export interface UseUserNotificationsOptions {
  userId: string;
  onNotification?: (event: WebSocketEvent) => void;
  onError?: (error: Error) => void;
}

export interface UseUserNotificationsReturn {
  notifications: NotificationData[];
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  clearNotifications: () => void;
  removeNotification: (id: string) => void;
}

export function useUserNotifications(options: UseUserNotificationsOptions): UseUserNotificationsReturn {
  const { userId, onNotification, onError } = options;

  const [notifications, setNotifications] = useState<NotificationData[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const connect = useCallback(async () => {
    if (!userId) return;

    setIsConnecting(true);
    setError(null);

    try {
      await websocketService.connectAsUser(userId, (event) => {
        // Create notification for important events
        if (
          event.type === WebSocketEventType.DELIVERY_COMPLETED ||
          event.type === WebSocketEventType.DRIVER_ASSIGNED ||
          event.type === WebSocketEventType.ORDER_STATUS_UPDATED
        ) {
          const notification: NotificationData = {
            id: `${Date.now()}-${Math.random()}`,
            type: NotificationType.INFO,
            title: getNotificationTitle(event.type),
            message: getNotificationMessage(event),
            timestamp: Date.now(),
            orderId: event.order_id,
            autoDismiss: true,
            dismissAfter: 5000,
          };

          setNotifications((prev) => [...prev, notification]);
        }

        if (event.type === WebSocketEventType.CONNECTED) {
          setIsConnected(true);
          setIsConnecting(false);
        } else if (event.type === WebSocketEventType.ERROR) {
          setError(new Error(event.message || 'WebSocket error'));
          onError?.(new Error(event.message || 'WebSocket error'));
        }

        onNotification?.(event);
      });
    } catch (err) {
      setIsConnecting(false);
      setError(err instanceof Error ? err : new Error('Failed to connect'));
      onError?.(err instanceof Error ? err : new Error('Failed to connect'));
    }
  }, [userId, onNotification, onError]);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setIsConnected(false);
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  // Auto-connect when userId changes
  useEffect(() => {
    if (userId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [userId]);

  // Auto-dismiss notifications
  useEffect(() => {
    const timers: NodeJS.Timeout[] = [];

    notifications.forEach((notification) => {
      if (notification.autoDismiss && notification.dismissAfter) {
        const timer = setTimeout(() => {
          removeNotification(notification.id);
        }, notification.dismissAfter);
        timers.push(timer);
      }
    });

    return () => {
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [notifications, removeNotification]);

  return {
    notifications,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    clearNotifications,
    removeNotification,
  };
}

// Helper functions
function getNotificationTitle(eventType: string): string {
  switch (eventType) {
    case WebSocketEventType.DELIVERY_COMPLETED:
      return 'Order Delivered!';
    case WebSocketEventType.DRIVER_ASSIGNED:
      return 'Driver Assigned';
    case WebSocketEventType.ORDER_STATUS_UPDATED:
      return 'Order Updated';
    default:
      return 'Notification';
  }
}

function getNotificationMessage(event: WebSocketEvent): string {
  switch (event.type) {
    case WebSocketEventType.DELIVERY_COMPLETED:
      return 'Your order has been delivered. Enjoy your meal!';
    case WebSocketEventType.DRIVER_ASSIGNED:
      return `A driver has been assigned to your order.${event.rider_name ? ` Driver: ${event.rider_name}` : ''}`;
    case WebSocketEventType.ORDER_STATUS_UPDATED:
      return `Your order status has been updated to: ${event.status}`;
    default:
      return 'You have a new notification';
  }
}

// Re-export types
export type {
  WebSocketEvent,
  WebSocketOptions,
  RoomType,
  OrderStatus,
  LocationData,
  OrderWithRealtime,
};
