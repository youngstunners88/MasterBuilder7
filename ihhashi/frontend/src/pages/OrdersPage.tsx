/**
 * OrdersPage
 * Displays user's orders with real-time status updates via WebSocket
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useOrderTracking, useUserNotifications } from '../hooks/useWebSocket';
import { notificationHelpers } from '../components/realtime';
import { RealTimeOrderTracker, NotificationToast } from '../components/realtime';
import { OrderWithRealtime, OrderStatus, NotificationData } from '../types/websocket';
import { ordersAPI } from '../lib/api';
import { useAuth } from '../App';

// Icons
const icons = {
  refresh: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
  orders: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
    </svg>
  ),
  empty: (
    <svg className="w-16 h-16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  ),
  back: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
  ),
  list: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
    </svg>
  ),
  grid: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  ),
};

// Order list item component
interface OrderListItemProps {
  order: OrderWithRealtime;
  isSelected: boolean;
  onClick: () => void;
}

const OrderListItem: React.FC<OrderListItemProps> = ({ order, isSelected, onClick }) => {
  const statusColors: Record<OrderStatus, string> = {
    [OrderStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
    [OrderStatus.CONFIRMED]: 'bg-blue-100 text-blue-800',
    [OrderStatus.PREPARING]: 'bg-orange-100 text-orange-800',
    [OrderStatus.READY]: 'bg-purple-100 text-purple-800',
    [OrderStatus.PICKED_UP]: 'bg-indigo-100 text-indigo-800',
    [OrderStatus.IN_TRANSIT]: 'bg-cyan-100 text-cyan-800',
    [OrderStatus.DELIVERED]: 'bg-green-100 text-green-800',
    [OrderStatus.CANCELLED]: 'bg-red-100 text-red-800',
  };

  return (
    <div
      onClick={onClick}
      className={`
        p-4 cursor-pointer transition-all duration-200 border-b border-gray-100
        hover:bg-gray-50
        ${isSelected ? 'bg-orange-50 border-l-4 border-l-orange-500' : 'border-l-4 border-l-transparent'}
      `}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="font-semibold text-gray-900">#{order.id.slice(-6).toUpperCase()}</p>
          <p className="text-sm text-gray-500">
            {new Date(order.created_at).toLocaleDateString('en-ZA')}
          </p>
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[order.status]}`}>
          {order.status}
        </span>
      </div>
      <div className="mt-2 flex items-center justify-between text-sm">
        <span className="text-gray-600">{order.items.length} items</span>
        <span className="font-semibold text-gray-900">R{order.total.toFixed(2)}</span>
      </div>
    </div>
  );
};

// Empty state component
const EmptyState: React.FC<{ onBrowse: () => void }> = ({ onBrowse }) => (
  <div className="flex flex-col items-center justify-center py-16 px-4">
    <div className="text-gray-300 mb-4">
      {icons.empty}
    </div>
    <h3 className="text-lg font-semibold text-gray-900 mb-2">No Orders Yet</h3>
    <p className="text-gray-500 text-center mb-6 max-w-sm">
      You haven't placed any orders yet. Browse our merchants and place your first order!
    </p>
    <button
      onClick={onBrowse}
      className="px-6 py-3 bg-orange-500 text-white font-medium rounded-lg hover:bg-orange-600 transition-colors"
    >
      Browse Restaurants
    </button>
  </div>
);

// Loading state component
const LoadingState: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="flex flex-col items-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mb-4" />
      <p className="text-gray-500">Loading your orders...</p>
    </div>
  </div>
);

export function OrdersPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // State
  const [orders, setOrders] = useState<OrderWithRealtime[]>([]);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'list' | 'detail'>('list');
  const [notifications, setNotifications] = useState<NotificationData[]>([]);

  // Get selected order
  const selectedOrder = orders.find(o => o.id === selectedOrderId) || null;

  // WebSocket tracking for selected order
  const {
    order: trackedOrder,
    isConnected: isOrderConnected,
    error: orderError,
  } = useOrderTracking({
    orderId: selectedOrderId || '',
    onStatusUpdate: (status, event) => {
      // Update order in list
      setOrders(prev => prev.map(o => 
        o.id === event.order_id 
          ? { ...o, status, status_history: event.status_history || o.status_history }
          : o
      ));
      
      // Add notification
      const notification = notificationHelpers.orderStatusUpdate(event.order_id!, status);
      addNotification(notification);
    },
    onLocationUpdate: (location, event) => {
      // Update order location
      setOrders(prev => prev.map(o => 
        o.id === event.order_id 
          ? { ...o, rider_location: location }
          : o
      ));
    },
    onDriverAssigned: (driverId, event) => {
      // Update order with driver info
      setOrders(prev => prev.map(o => 
        o.id === event.order_id 
          ? { 
              ...o, 
              rider_id: driverId,
              rider_name: event.rider_name,
              rider_phone: event.rider_phone,
            }
          : o
      ));
      
      // Add notification
      const notification = notificationHelpers.driverAssigned(event.order_id!, event.rider_name);
      addNotification(notification);
    },
    onDeliveryComplete: (event) => {
      // Update order status
      setOrders(prev => prev.map(o => 
        o.id === event.order_id 
          ? { ...o, status: OrderStatus.DELIVERED }
          : o
      ));
      
      // Add notification
      const notification = notificationHelpers.deliveryCompleted(event.order_id!);
      addNotification(notification);
    },
  });

  // User notifications via WebSocket
  const { notifications: wsNotifications } = useUserNotifications({
    userId: user?.id || '',
    onNotification: (event) => {
      // Handle user-level notifications
      console.log('User notification:', event);
    },
  });

  // Merge WebSocket notifications
  useEffect(() => {
    if (wsNotifications.length > 0) {
      setNotifications(prev => [...prev, ...wsNotifications]);
    }
  }, [wsNotifications]);

  // Fetch orders on mount
  useEffect(() => {
    fetchOrders();
  }, []);

  // Fetch orders function
  const fetchOrders = async () => {
    setIsLoading(true);
    try {
      const response = await ordersAPI.list({ limit: 50 });
      setOrders(response.data.orders || []);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Add notification helper
  const addNotification = (notification: Omit<NotificationData, 'id' | 'timestamp'>) => {
    const newNotification: NotificationData = {
      ...notification,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: Date.now(),
    };
    setNotifications(prev => [...prev, newNotification]);
  };

  // Remove notification
  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  // Handle order selection
  const handleSelectOrder = (orderId: string) => {
    setSelectedOrderId(orderId);
    setViewMode('detail');
  };

  // Handle back to list
  const handleBackToList = () => {
    setSelectedOrderId(null);
    setViewMode('list');
  };

  // Merge tracked order data with list data
  const displayOrder = trackedOrder || selectedOrder;

  if (isLoading) {
    return <LoadingState />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {viewMode === 'detail' && (
                <button
                  onClick={handleBackToList}
                  className="p-2 -ml-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  {icons.back}
                </button>
              )}
              <div className="flex items-center gap-2">
                {icons.orders}
                <h1 className="text-xl font-bold text-gray-900">
                  {viewMode === 'list' ? 'My Orders' : 'Order Details'}
                </h1>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {viewMode === 'list' && (
                <>
                  <span className="text-sm text-gray-500">
                    {orders.length} order{orders.length !== 1 ? 's' : ''}
                  </span>
                  <button
                    onClick={fetchOrders}
                    className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    title="Refresh"
                  >
                    {icons.refresh}
                  </button>
                </>
              )}
              {isOrderConnected && viewMode === 'detail' && (
                <span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-full">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  Live
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {orders.length === 0 ? (
          <EmptyState onBrowse={() => navigate('/')} />
        ) : viewMode === 'list' ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {orders.map(order => (
              <div
                key={order.id}
                onClick={() => handleSelectOrder(order.id)}
                className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden cursor-pointer hover:shadow-md transition-shadow"
              >
                <OrderListItem
                  order={order}
                  isSelected={false}
                  onClick={() => handleSelectOrder(order.id)}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-3">
            {/* Order List Sidebar */}
            <div className="hidden lg:block lg:col-span-1">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="p-4 border-b border-gray-100">
                  <h2 className="font-semibold text-gray-900">Recent Orders</h2>
                </div>
                <div className="max-h-[calc(100vh-300px)] overflow-y-auto">
                  {orders.map(order => (
                    <OrderListItem
                      key={order.id}
                      order={order}
                      isSelected={order.id === selectedOrderId}
                      onClick={() => handleSelectOrder(order.id)}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Order Details */}
            <div className="lg:col-span-2">
              <RealTimeOrderTracker
                order={displayOrder}
                isConnected={isOrderConnected}
                error={orderError}
                onRefresh={() => fetchOrders()}
              />
            </div>
          </div>
        )}
      </main>

      {/* Notification Toast */}
      <NotificationToast
        notifications={notifications}
        onDismiss={removeNotification}
        position="top-right"
      />
    </div>
  );
}

export default OrdersPage;
