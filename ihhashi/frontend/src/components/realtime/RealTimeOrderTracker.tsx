/**
 * RealTimeOrderTracker Component
 * Displays live order status updates with progress indicator
 */
import React, { useMemo } from 'react';
import {
  OrderStatus,
  OrderWithRealtime,
  LocationData,
} from '../../types/websocket';

// Icons (using SVG for zero dependency)
const icons = {
  pending: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  confirmed: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  preparing: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  ),
  ready: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  picked_up: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  in_transit: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 7m0 13V7" />
    </svg>
  ),
  delivered: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  ),
  cancelled: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  location: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  driver: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  ),
  time: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  connecting: (
    <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
  ),
};

// Order steps for progress bar
const orderSteps: OrderStatus[] = [
  OrderStatus.PENDING,
  OrderStatus.CONFIRMED,
  OrderStatus.PREPARING,
  OrderStatus.READY,
  OrderStatus.PICKED_UP,
  OrderStatus.IN_TRANSIT,
  OrderStatus.DELIVERED,
];

// Status labels
const statusLabels: Record<OrderStatus, string> = {
  [OrderStatus.PENDING]: 'Order Received',
  [OrderStatus.CONFIRMED]: 'Confirmed',
  [OrderStatus.PREPARING]: 'Preparing',
  [OrderStatus.READY]: 'Ready for Pickup',
  [OrderStatus.PICKED_UP]: 'Picked Up',
  [OrderStatus.IN_TRANSIT]: 'On the Way',
  [OrderStatus.DELIVERED]: 'Delivered',
  [OrderStatus.CANCELLED]: 'Cancelled',
};

// Status descriptions
const statusDescriptions: Record<OrderStatus, string> = {
  [OrderStatus.PENDING]: 'Waiting for restaurant to confirm your order',
  [OrderStatus.CONFIRMED]: 'Restaurant has confirmed your order',
  [OrderStatus.PREPARING]: 'Your food is being prepared',
  [OrderStatus.READY]: 'Your order is ready for pickup by driver',
  [OrderStatus.PICKED_UP]: 'Driver has picked up your order',
  [OrderStatus.IN_TRANSIT]: 'Driver is on the way to your location',
  [OrderStatus.DELIVERED]: 'Your order has been delivered!',
  [OrderStatus.CANCELLED]: 'This order has been cancelled',
};

// Status colors
const statusColors: Record<OrderStatus, { bg: string; text: string; border: string }> = {
  [OrderStatus.PENDING]: { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300' },
  [OrderStatus.CONFIRMED]: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300' },
  [OrderStatus.PREPARING]: { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300' },
  [OrderStatus.READY]: { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-300' },
  [OrderStatus.PICKED_UP]: { bg: 'bg-indigo-100', text: 'text-indigo-800', border: 'border-indigo-300' },
  [OrderStatus.IN_TRANSIT]: { bg: 'bg-cyan-100', text: 'text-cyan-800', border: 'border-cyan-300' },
  [OrderStatus.DELIVERED]: { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300' },
  [OrderStatus.CANCELLED]: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' },
};

export interface RealTimeOrderTrackerProps {
  order: OrderWithRealtime | null;
  isConnected?: boolean;
  isConnecting?: boolean;
  error?: Error | null;
  className?: string;
  showMap?: boolean;
  onRefresh?: () => void;
}

export const RealTimeOrderTracker: React.FC<RealTimeOrderTrackerProps> = ({
  order,
  isConnected = true,
  isConnecting = false,
  error = null,
  className = '',
  showMap = true,
  onRefresh,
}) => {
  // Calculate progress percentage
  const progressPercent = useMemo(() => {
    if (!order) return 0;
    if (order.status === OrderStatus.CANCELLED) return 0;
    
    const currentIndex = orderSteps.indexOf(order.status);
    if (currentIndex === -1) return 0;
    
    return ((currentIndex + 1) / orderSteps.length) * 100;
  }, [order?.status]);

  // Calculate estimated arrival
  const estimatedArrival = useMemo(() => {
    if (!order?.estimated_delivery) return null;
    const date = new Date(order.estimated_delivery);
    return date.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' });
  }, [order?.estimated_delivery]);

  // Format status history time
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-ZA', { hour: '2-digit', minute: '2-digit' });
  };

  // Calculate distance (mock - would use actual geolocation in production)
  const calculateDistance = (location?: LocationData) => {
    if (!location) return null;
    // This is a placeholder - real implementation would calculate actual distance
    return '2.5 km away';
  };

  if (!order) {
    return (
      <div className={`bg-white rounded-xl shadow-sm border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center h-32 text-gray-400">
          <div className="text-center">
            {icons.pending}
            <p className="mt-2 text-sm">No order information available</p>
          </div>
        </div>
      </div>
    );
  }

  const colors = statusColors[order.status];

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              Order #{order.id.slice(-6).toUpperCase()}
            </h3>
            <p className="text-sm text-gray-500">
              Placed {new Date(order.created_at).toLocaleDateString('en-ZA')}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isConnecting && (
              <span className="flex items-center gap-1 text-sm text-yellow-600" title="Connecting...">
                {icons.connecting}
              </span>
            )}
            {!isConnected && !isConnecting && (
              <span className="flex items-center gap-1 text-sm text-red-600" title="Disconnected">
                {icons.error}
              </span>
            )}
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors.bg} ${colors.text}`}>
              {statusLabels[order.status]}
            </span>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="px-6 py-3 bg-red-50 border-b border-red-100">
          <div className="flex items-center gap-2 text-red-700">
            {icons.error}
            <span className="text-sm">{error.message}</span>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="ml-auto text-sm font-medium hover:underline"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      )}

      {/* Progress Bar */}
      {order.status !== OrderStatus.CANCELLED && (
        <div className="px-6 py-4">
          <div className="relative">
            {/* Background bar */}
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              {/* Progress bar */}
              <div
                className="h-full bg-gradient-to-r from-orange-500 to-orange-400 transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            
            {/* Step indicators */}
            <div className="flex justify-between mt-2">
              {orderSteps.map((step, index) => {
                const isCompleted = index <= orderSteps.indexOf(order.status);
                const isCurrent = step === order.status;
                
                return (
                  <div
                    key={step}
                    className={`flex flex-col items-center ${
                      index >= orderSteps.length - 1 ? 'hidden sm:flex' : 'flex'
                    }`}
                    style={{ width: `${100 / (orderSteps.length - 1)}%` }}
                  >
                    <div
                      className={`w-3 h-3 rounded-full border-2 transition-colors duration-300 ${
                        isCompleted
                          ? 'bg-orange-500 border-orange-500'
                          : isCurrent
                          ? 'bg-white border-orange-500'
                          : 'bg-gray-200 border-gray-300'
                      }`}
                    />
                    <span
                      className={`text-xs mt-1 hidden lg:block ${
                        isCompleted || isCurrent ? 'text-gray-700 font-medium' : 'text-gray-400'
                      }`}
                    >
                      {statusLabels[step]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Status Description */}
      <div className={`px-6 py-4 ${colors.bg} border-y ${colors.border}`}>
        <div className="flex items-start gap-3">
          <div className={`${colors.text} mt-0.5`}>
            {icons[order.status] || icons.pending}
          </div>
          <div>
            <p className={`font-medium ${colors.text}`}>{statusLabels[order.status]}</p>
            <p className="text-sm text-gray-600 mt-1">
              {statusDescriptions[order.status]}
            </p>
          </div>
        </div>
      </div>

      {/* Driver Information */}
      {order.rider_id && order.status !== OrderStatus.CANCELLED && order.status !== OrderStatus.DELIVERED && (
        <div className="px-6 py-4 border-b border-gray-100">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Delivery Partner</h4>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-gray-200 flex items-center justify-center">
              {icons.driver}
            </div>
            <div className="flex-1">
              <p className="font-medium text-gray-900">{order.rider_name || 'Driver'}</p>
              {order.rider_phone && (
                <p className="text-sm text-gray-500">{order.rider_phone}</p>
              )}
              {order.rider_location && (
                <div className="flex items-center gap-1 text-sm text-orange-600 mt-1">
                  {icons.location}
                  <span>{calculateDistance(order.rider_location)}</span>
                </div>
              )}
            </div>
            {estimatedArrival && (
              <div className="text-right">
                <p className="text-sm text-gray-500">Est. Arrival</p>
                <p className="text-lg font-semibold text-orange-600">{estimatedArrival}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Order Items */}
      <div className="px-6 py-4 border-b border-gray-100">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Order Items</h4>
        <div className="space-y-2">
          {order.items.map((item, index) => (
            <div key={index} className="flex justify-between text-sm">
              <span className="text-gray-700">
                {item.quantity}x {item.product_name}
              </span>
              <span className="text-gray-900 font-medium">
                R{(item.total_price || item.quantity * item.unit_price).toFixed(2)}
              </span>
            </div>
          ))}
        </div>
        <div className="mt-3 pt-3 border-t border-gray-100 space-y-1">
          <div className="flex justify-between text-sm text-gray-600">
            <span>Subtotal</span>
            <span>R{order.subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-sm text-gray-600">
            <span>Delivery Fee</span>
            <span>R{order.delivery_fee.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-base font-semibold text-gray-900 pt-1">
            <span>Total</span>
            <span>R{order.total.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Delivery Address */}
      <div className="px-6 py-4 border-b border-gray-100">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Delivery Address</h4>
        <div className="flex items-start gap-2">
          {icons.location}
          <div className="text-sm text-gray-700">
            <p className="font-medium">{order.delivery_info.address_label}</p>
            <p>{order.delivery_info.address_line1}</p>
            {order.delivery_info.address_line2 && <p>{order.delivery_info.address_line2}</p>}
            <p>{order.delivery_info.city}</p>
          </div>
        </div>
      </div>

      {/* Status History */}
      {order.status_history && order.status_history.length > 0 && (
        <div className="px-6 py-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Status History</h4>
          <div className="space-y-3">
            {order.status_history.map((history, index) => (
              <div key={index} className="flex items-center gap-3 text-sm">
                <span className="text-gray-400 flex items-center gap-1">
                  {icons.time}
                  {formatTime(history.timestamp)}
                </span>
                <span className="text-gray-700">
                  {statusLabels[history.status] || history.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Map Placeholder */}
      {showMap && order.rider_location && order.status !== OrderStatus.DELIVERED && (
        <div className="px-6 pb-6">
          <DriverLocationMap 
            driverLocation={order.rider_location}
            driverName={order.rider_name}
          />
        </div>
      )}
    </div>
  );
};

// Simple map component
interface DriverLocationMapProps {
  driverLocation: LocationData;
  driverName?: string;
  className?: string;
}

const DriverLocationMap: React.FC<DriverLocationMapProps> = ({
  driverLocation,
  driverName,
  className = '',
}) => {
  return (
    <div className={`bg-gray-100 rounded-lg overflow-hidden ${className}`}>
      <div className="p-3 bg-gray-800 text-white flex items-center justify-between">
        <span className="text-sm font-medium">Live Location</span>
        <span className="flex items-center gap-1 text-xs">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          Live
        </span>
      </div>
      <div className="h-48 bg-gray-200 relative flex items-center justify-center">
        {/* Simple map visualization - in production, use Google Maps or Mapbox */}
        <div className="text-center text-gray-500">
          <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 7m0 13V7" />
          </svg>
          <p className="text-sm font-medium">
            {driverName ? `${driverName} is nearby` : 'Driver is nearby'}
          </p>
          <p className="text-xs mt-1">
            Lat: {driverLocation.latitude.toFixed(4)}, Lng: {driverLocation.longitude.toFixed(4)}
          </p>
          {driverLocation.speed !== undefined && (
            <p className="text-xs">
              Speed: {driverLocation.speed.toFixed(1)} km/h
            </p>
          )}
        </div>
        
        {/* Driver marker */}
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
          <div className="relative">
            <div className="w-4 h-4 bg-orange-500 rounded-full border-2 border-white shadow-lg" />
            <div className="absolute inset-0 w-4 h-4 bg-orange-500 rounded-full animate-ping opacity-75" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default RealTimeOrderTracker;
