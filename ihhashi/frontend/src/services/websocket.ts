/**
 * WebSocket Service
 * Handles real-time communication with the backend
 */
import {
  WebSocketEventType,
  RoomType,
  ConnectionStatus,
  WebSocketOptions,
  WebSocketEvent,
  LocationData,
  OrderStatus,
} from '../types/websocket';

/**
 * Get the WebSocket base URL from the API URL
 */
const getWebSocketURL = (): string => {
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const wsProtocol = apiUrl.startsWith('https') ? 'wss' : 'ws';
  const baseUrl = apiUrl.replace(/^https?:\/\//, '');
  return `${wsProtocol}://${baseUrl}`;
};

/**
 * Get authentication token from localStorage
 */
const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token');
};

/**
 * WebSocket Service Class
 * Manages WebSocket connections with automatic reconnection
 */
class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string = '';
  private options: WebSocketOptions = {};
  private reconnectCount: number = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private pongReceived: boolean = true;
  private messageHandlers: Map<string, Set<(event: WebSocketEvent) => void>> = new Map();
  private connectionStatus: ConnectionStatus = ConnectionStatus.DISCONNECTED;
  private subscribedRooms: Set<string> = new Set();
  private pendingMessages: Array<WebSocketEvent> = [];

  // Default options
  private defaultOptions: WebSocketOptions = {
    autoReconnect: true,
    reconnectAttempts: 5,
    reconnectInterval: 3000,
    heartbeatInterval: 25000,
  };

  /**
   * Get current connection status
   */
  getStatus(): ConnectionStatus {
    return this.connectionStatus;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.connectionStatus === ConnectionStatus.CONNECTED && 
           this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Connect to WebSocket
   */
  connect(endpoint: string = '/ws', options: WebSocketOptions = {}): Promise<void> {
    return new Promise((resolve, reject) => {
      this.options = { ...this.defaultOptions, ...options };
      
      if (this.isConnected()) {
        resolve();
        return;
      }

      this.connectionStatus = ConnectionStatus.CONNECTING;
      
      const token = getAuthToken();
      if (!token) {
        this.connectionStatus = ConnectionStatus.ERROR;
        reject(new Error('Authentication token not found'));
        return;
      }

      this.url = `${getWebSocketURL()}${endpoint}?token=${encodeURIComponent(token)}`;
      
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          console.log('[WebSocket] Connected');
          this.connectionStatus = ConnectionStatus.CONNECTED;
          this.reconnectCount = 0;
          this.startHeartbeat();
          this.processPendingMessages();
          this.resubscribeToRooms();
          this.options.onConnect?.();
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          this.connectionStatus = ConnectionStatus.ERROR;
          this.options.onError?.(error);
          reject(error);
        };

        this.ws.onclose = (event) => {
          console.log('[WebSocket] Disconnected:', event.code, event.reason);
          this.connectionStatus = ConnectionStatus.DISCONNECTED;
          this.stopHeartbeat();
          this.options.onDisconnect?.();
          
          if (this.options.autoReconnect && this.reconnectCount < (this.options.reconnectAttempts || 5)) {
            this.attemptReconnect(endpoint);
          }
        };
      } catch (error) {
        this.connectionStatus = ConnectionStatus.ERROR;
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.options.autoReconnect = false;
    this.stopHeartbeat();
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnected');
      this.ws = null;
    }
    
    this.connectionStatus = ConnectionStatus.DISCONNECTED;
    this.subscribedRooms.clear();
  }

  /**
   * Attempt to reconnect
   */
  private attemptReconnect(endpoint: string): void {
    this.reconnectCount++;
    this.connectionStatus = ConnectionStatus.RECONNECTING;
    
    console.log(`[WebSocket] Reconnecting... Attempt ${this.reconnectCount}/${this.options.reconnectAttempts}`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect(endpoint, this.options).catch(() => {
        // Reconnection failed, will try again if attempts remain
      });
    }, this.options.reconnectInterval);
  }

  /**
   * Start heartbeat interval
   */
  private startHeartbeat(): void {
    if (!this.options.heartbeatInterval) return;
    
    this.heartbeatTimer = setInterval(() => {
      if (!this.pongReceived) {
        console.log('[WebSocket] No pong received, reconnecting...');
        this.ws?.close(1000, 'Heartbeat timeout');
        return;
      }
      
      this.pongReceived = false;
      this.send({ type: WebSocketEventType.PING });
    }, this.options.heartbeatInterval);
  }

  /**
   * Stop heartbeat interval
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * Handle incoming message
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data: WebSocketEvent = JSON.parse(event.data);
      
      // Handle pong
      if (data.type === WebSocketEventType.PONG) {
        this.pongReceived = true;
        return;
      }
      
      // Handle heartbeat from server
      if (data.type === WebSocketEventType.HEARTBEAT) {
        this.send({ type: WebSocketEventType.PONG });
        return;
      }
      
      console.log('[WebSocket] Message received:', data.type);
      
      // Call global message handler
      this.options.onMessage?.(data);
      
      // Call specific handlers
      this.callHandlers(data.type, data);
      
      // Also call wildcard handlers
      this.callHandlers('*', data);
    } catch (error) {
      console.error('[WebSocket] Error parsing message:', error);
    }
  }

  /**
   * Call registered handlers for an event type
   */
  private callHandlers(type: string, data: WebSocketEvent): void {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          console.error(`[WebSocket] Error in handler for ${type}:`, error);
        }
      });
    }
  }

  /**
   * Send message to server
   */
  send(message: Partial<WebSocketEvent>): boolean {
    if (this.isConnected()) {
      try {
        this.ws!.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('[WebSocket] Send error:', error);
        return false;
      }
    } else {
      // Queue message for later
      this.pendingMessages.push(message as WebSocketEvent);
      return false;
    }
  }

  /**
   * Process pending messages after connection
   */
  private processPendingMessages(): void {
    while (this.pendingMessages.length > 0) {
      const message = this.pendingMessages.shift();
      if (message) {
        this.send(message);
      }
    }
  }

  /**
   * Subscribe to a room
   */
  subscribe(roomType: RoomType, roomId: string, isOwner: boolean = false): void {
    const roomKey = `${roomType}:${roomId}`;
    this.subscribedRooms.add(roomKey);
    
    this.send({
      type: WebSocketEventType.SUBSCRIBE,
      room_type: roomType,
      room_id: roomId,
      is_owner: isOwner,
    });
  }

  /**
   * Unsubscribe from a room
   */
  unsubscribe(roomType: RoomType, roomId: string): void {
    const roomKey = `${roomType}:${roomId}`;
    this.subscribedRooms.delete(roomKey);
    
    this.send({
      type: WebSocketEventType.UNSUBSCRIBE,
      room_type: roomType,
      room_id: roomId,
    });
  }

  /**
   * Resubscribe to all rooms after reconnection
   */
  private resubscribeToRooms(): void {
    this.subscribedRooms.forEach((roomKey) => {
      const [roomType, roomId] = roomKey.split(':') as [RoomType, string];
      this.subscribe(roomType, roomId);
    });
  }

  /**
   * Register message handler
   */
  on(type: string, handler: (event: WebSocketEvent) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set());
    }
    
    this.messageHandlers.get(type)!.add(handler);
    
    // Return unsubscribe function
    return () => {
      this.off(type, handler);
    };
  }

  /**
   * Remove message handler
   */
  off(type: string, handler: (event: WebSocketEvent) => void): void {
    const handlers = this.messageHandlers.get(type);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Remove all handlers for a type
   */
  offAll(type?: string): void {
    if (type) {
      this.messageHandlers.delete(type);
    } else {
      this.messageHandlers.clear();
    }
  }

  // =============================================================================
  // Convenience Methods
  // =============================================================================

  /**
   * Connect to order tracking
   */
  trackOrder(orderId: string, onUpdate?: (event: WebSocketEvent) => void): Promise<void> {
    return new Promise((resolve, reject) => {
      const connectAndTrack = () => {
        this.connect(`/track/${orderId}`, {
          ...this.options,
          onConnect: () => {
            this.options.onConnect?.();
            resolve();
          },
          onMessage: (event) => {
            onUpdate?.(event);
            this.options.onMessage?.(event);
          },
        }).catch(reject);
      };

      if (this.isConnected()) {
        this.disconnect();
      }
      
      connectAndTrack();
    });
  }

  /**
   * Connect as rider
   */
  connectAsRider(
    riderId: string,
    onOrderAssigned?: (event: WebSocketEvent) => void,
    onMessage?: (event: WebSocketEvent) => void
  ): Promise<void> {
    return this.connect(`/rider/${riderId}`, {
      ...this.options,
      onMessage: (event) => {
        if (event.type === WebSocketEventType.DRIVER_ASSIGNED) {
          onOrderAssigned?.(event);
        }
        onMessage?.(event);
      },
    });
  }

  /**
   * Connect as merchant
   */
  connectAsMerchant(
    merchantId: string,
    onNewOrder?: (event: WebSocketEvent) => void,
    onMessage?: (event: WebSocketEvent) => void
  ): Promise<void> {
    return this.connect(`/merchant/${merchantId}`, {
      ...this.options,
      onMessage: (event) => {
        if (event.type === WebSocketEventType.ORDER_CREATED) {
          onNewOrder?.(event);
        }
        onMessage?.(event);
      },
    });
  }

  /**
   * Connect for user notifications
   */
  connectAsUser(
    userId: string,
    onNotification?: (event: WebSocketEvent) => void
  ): Promise<void> {
    return this.connect(`/user/${userId}`, {
      ...this.options,
      onMessage: (event) => {
        onNotification?.(event);
      },
    });
  }

  /**
   * Update driver location
   */
  updateLocation(location: LocationData): boolean {
    return this.send({
      type: WebSocketEventType.DRIVER_LOCATION_UPDATE,
      location,
    });
  }

  /**
   * Update driver status
   */
  updateStatus(status: 'available' | 'busy' | 'offline' | 'break'): boolean {
    return this.send({
      type: WebSocketEventType.DRIVER_STATUS_UPDATE,
      status,
    });
  }

  /**
   * Send chat message
   */
  sendMessage(orderId: string, message: string): boolean {
    return this.send({
      type: WebSocketEventType.NEW_MESSAGE,
      order_id: orderId,
      message,
    });
  }

  /**
   * Accept order (rider)
   */
  acceptOrder(orderId: string): boolean {
    return this.send({
      type: 'accept_order',
      order_id: orderId,
    });
  }

  /**
   * Complete delivery (rider)
   */
  completeDelivery(orderId: string): boolean {
    return this.send({
      type: 'complete_delivery',
      order_id: orderId,
    });
  }

  /**
   * Update order status (merchant)
   */
  updateOrderStatus(orderId: string, status: OrderStatus): boolean {
    return this.send({
      type: WebSocketEventType.ORDER_STATUS_UPDATED,
      order_id: orderId,
      status,
    });
  }

  /**
   * Request current location
   */
  requestLocation(): boolean {
    return this.send({
      type: WebSocketEventType.GET_LOCATION,
    });
  }

  /**
   * Request current order status
   */
  requestStatus(): boolean {
    return this.send({
      type: WebSocketEventType.GET_STATUS,
    });
  }
}

// Create singleton instance
export const websocketService = new WebSocketService();

// Export class for testing or multiple instances
export { WebSocketService };
