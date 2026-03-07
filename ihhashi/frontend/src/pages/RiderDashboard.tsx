/**
 * RiderDashboard
 * Dashboard for delivery riders with real-time location tracking and order management
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useRiderTracking } from '../hooks/useWebSocket';
import { DriverLocationMap, NotificationToast, useNotifications, notificationHelpers } from '../components/realtime';
import { LocationData, OrderStatus, NotificationType } from '../types/websocket';
import { riderAPI } from '../lib/api';
import { useAuth } from '../App';
import DeliveryModeIcon from '../components/delivery/DeliveryModeIcon';

// Icons
const LocationIcon = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" /></svg>;
const OrderIcon = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>;
const CheckIcon = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>;
const PackageIcon = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" /></svg>;
const PhoneIcon = () => <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" /></svg>;

type RiderStatus = 'offline' | 'available' | 'busy';
type DeliveryMode = 'walking' | 'skateboard' | 'bicycle' | 'motorbike';

interface ActiveOrder {
  id: string;
  status: OrderStatus;
  pickup_address: string;
  delivery_address: string;
  customer_name: string;
  customer_phone: string;
  items: Array<{ name: string; quantity: number }>;
  total: number;
  earnings: number;
  restaurant_name: string;
  restaurant_phone?: string;
  created_at: string;
}

export function RiderDashboard() {
  const { user } = useAuth();
  const [status, setStatus] = useState<RiderStatus>('offline');
  const [deliveryMode, setDeliveryMode] = useState<DeliveryMode>('bicycle');
  const [activeOrder, setActiveOrder] = useState<ActiveOrder | null>(null);
  const [currentLocation, setCurrentLocation] = useState<LocationData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const locationWatchId = useRef<number | null>(null);
  const notifs = useNotifications();

  const {
    isConnected,
    isConnecting,
    updateLocation: wsUpdateLocation,
    updateStatus: wsUpdateStatus,
    completeDelivery: wsCompleteDelivery,
  } = useRiderTracking({
    riderId: user?.id || '',
    onOrderAssigned: (orderId) => {
      notifs.addNotification(notificationHelpers.driverAssigned(orderId));
      fetchActiveOrder();
    },
    onError: () => {
      notifs.addNotification({
        type: NotificationType.ERROR,
        title: 'Connection Error',
        message: 'Failed to connect to server. Please check your connection.',
        autoDismiss: true,
        dismissAfter: 5000,
      });
    },
  });

  const fetchActiveOrder = useCallback(async () => {
    try {
      const response = await riderAPI.profile();
      if (response.data.active_order) {
        setActiveOrder(response.data.active_order);
        setStatus('busy');
      } else {
        setActiveOrder(null);
        if (status === 'busy') setStatus('available');
      }
    } catch {
      // Silently handle error
    }
  }, [status]);

  useEffect(() => {
    fetchActiveOrder();
    setIsLoading(false);
  }, []);

  useEffect(() => {
    if (status === 'available' || status === 'busy') {
      startLocationTracking();
    } else {
      stopLocationTracking();
    }
    return () => stopLocationTracking();
  }, [status]);

  useEffect(() => {
    if (currentLocation && isConnected) {
      wsUpdateLocation(currentLocation);
    }
  }, [currentLocation, isConnected, wsUpdateLocation]);

  const startLocationTracking = () => {
    if (!navigator.geolocation) {
      notifs.addNotification({
        type: NotificationType.ERROR,
        title: 'Location Error',
        message: 'Geolocation is not supported by your browser.',
        autoDismiss: true,
        dismissAfter: 5000,
      });
      return;
    }

    locationWatchId.current = navigator.geolocation.watchPosition(
      (position) => {
        setCurrentLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          heading: position.coords.heading || undefined,
          speed: position.coords.speed ? position.coords.speed * 3.6 : undefined,
          last_updated: new Date().toISOString(),
        });
      },
      () => {
        notifs.addNotification({
          type: NotificationType.ERROR,
          title: 'Location Error',
          message: 'Unable to get your location. Please enable location services.',
          autoDismiss: true,
          dismissAfter: 5000,
        });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
    );
  };

  const stopLocationTracking = () => {
    if (locationWatchId.current !== null) {
      navigator.geolocation.clearWatch(locationWatchId.current);
      locationWatchId.current = null;
    }
  };

  const handleStatusChange = (newStatus: RiderStatus) => {
    setStatus(newStatus);
    if (isConnected) {
      wsUpdateStatus(newStatus);
    }
  };

  const handleCompleteDelivery = async () => {
    if (!activeOrder) return;
    
    try {
      wsCompleteDelivery(activeOrder.id);
      notifs.addNotification(notificationHelpers.deliveryCompleted(activeOrder.id));
      setActiveOrder(null);
      setStatus('available');
    } catch {
      notifs.addNotification({
        type: NotificationType.ERROR,
        title: 'Error',
        message: 'Failed to complete delivery. Please try again.',
        autoDismiss: true,
        dismissAfter: 5000,
      });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center text-white">
                <LocationIcon />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Driver Dashboard</h1>
                <p className="text-sm text-gray-500">{user?.full_name || 'Driver'}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Connection Status */}
              <div className={`flex items-center gap-1 text-sm ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                {isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Disconnected'}
              </div>

              {/* Status Toggle */}
              <select
                value={status}
                onChange={(e) => handleStatusChange(e.target.value as RiderStatus)}
                className="px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-orange-500"
              >
                <option value="offline">Offline</option>
                <option value="available">Available</option>
                <option value="busy" disabled>On Delivery</option>
              </select>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column - Stats */}
          <div className="space-y-4">
            {/* Status Card */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-3">Current Status</h3>
              <div className={`flex items-center gap-3 p-3 rounded-lg ${
                status === 'available' ? 'bg-green-50' : 
                status === 'busy' ? 'bg-orange-50' : 'bg-gray-50'
              }`}>
                <div className={`w-3 h-3 rounded-full ${
                  status === 'available' ? 'bg-green-500' : 
                  status === 'busy' ? 'bg-orange-500' : 'bg-gray-400'
                }`} />
                <span className="font-medium capitalize">{status}</span>
              </div>
            </div>

            {/* Location Card */}
            {currentLocation && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
                <h3 className="text-sm font-medium text-gray-500 mb-3">Current Location</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Latitude</span>
                    <span className="font-mono">{currentLocation.latitude.toFixed(6)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Longitude</span>
                    <span className="font-mono">{currentLocation.longitude.toFixed(6)}</span>
                  </div>
                  {currentLocation.speed !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Speed</span>
                      <span>{currentLocation.speed.toFixed(1)} km/h</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <button
                  onClick={() => handleStatusChange('available')}
                  disabled={status === 'available'}
                  className="w-full flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <CheckIcon />
                  Go Online
                </button>
                <button
                  onClick={() => handleStatusChange('offline')}
                  disabled={status === 'offline'}
                  className="w-full flex items-center gap-2 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Go Offline
                </button>
              </div>
            </div>

            {/* Delivery Mode Selector */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-3">Delivery Mode</h3>
              <div className="grid grid-cols-2 gap-3">
                {(['walking', 'skateboard', 'bicycle', 'motorbike'] as DeliveryMode[]).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setDeliveryMode(mode)}
                    className={`flex flex-col items-center gap-2 p-3 rounded-xl transition-all ${
                      deliveryMode === mode
                        ? 'bg-primary/20 border-2 border-primary'
                        : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                    }`}
                  >
                    <DeliveryModeIcon mode={mode} size="md" />
                    <span className={`text-xs font-medium capitalize ${
                      deliveryMode === mode ? 'text-secondary' : 'text-gray-600'
                    }`}>
                      {mode}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Center/Right - Active Order */}
          <div className="lg:col-span-2">
            {activeOrder ? (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="p-4 border-b border-gray-100 bg-orange-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <PackageIcon />
                      <h2 className="font-semibold text-gray-900">Active Delivery</h2>
                    </div>
                    <span className="px-3 py-1 bg-orange-500 text-white text-sm font-medium rounded-full">
                      {activeOrder.status}
                    </span>
                  </div>
                </div>

                <div className="p-4 space-y-4">
                  {/* Order Details */}
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-sm text-gray-500">Order ID</p>
                      <p className="font-medium">#{activeOrder.id.slice(-6).toUpperCase()}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Restaurant</p>
                      <p className="font-medium">{activeOrder.restaurant_name}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Customer</p>
                      <p className="font-medium">{activeOrder.customer_name}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Earnings</p>
                      <p className="font-medium text-green-600">R{activeOrder.earnings.toFixed(2)}</p>
                    </div>
                  </div>

                  {/* Addresses */}
                  <div className="space-y-3">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500 uppercase mb-1">Pickup</p>
                      <p className="text-sm font-medium">{activeOrder.pickup_address}</p>
                      {activeOrder.restaurant_phone && (
                        <a href={`tel:${activeOrder.restaurant_phone}`} className="inline-flex items-center gap-1 text-sm text-orange-600 mt-2">
                          <PhoneIcon /> Call Restaurant
                        </a>
                      )}
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-xs text-gray-500 uppercase mb-1">Deliver To</p>
                      <p className="text-sm font-medium">{activeOrder.delivery_address}</p>
                      <a href={`tel:${activeOrder.customer_phone}`} className="inline-flex items-center gap-1 text-sm text-orange-600 mt-2">
                        <PhoneIcon /> Call Customer
                      </a>
                    </div>
                  </div>

                  {/* Items */}
                  <div>
                    <p className="text-sm text-gray-500 mb-2">Items</p>
                    <ul className="space-y-1">
                      {activeOrder.items.map((item, idx) => (
                        <li key={idx} className="text-sm flex justify-between">
                          <span>{item.quantity}x {item.name}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Map */}
                  {currentLocation && (
                    <DriverLocationMap
                      driverLocation={currentLocation}
                      driverName={user?.full_name}
                      height={250}
                    />
                  )}

                  {/* Complete Button */}
                  <button
                    onClick={handleCompleteDelivery}
                    className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-green-500 text-white font-medium rounded-lg hover:bg-green-600 transition-colors"
                  >
                    <CheckIcon />
                    Mark as Delivered
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <OrderIcon />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">No Active Delivery</h3>
                <p className="text-gray-500 mb-4">
                  {status === 'available' 
                    ? 'You are online and ready to receive orders.' 
                    : 'Go online to start receiving delivery requests.'}
                </p>
                {status !== 'available' && (
                  <button
                    onClick={() => handleStatusChange('available')}
                    className="px-6 py-2 bg-orange-500 text-white font-medium rounded-lg hover:bg-orange-600 transition-colors"
                  >
                    Go Online
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Notifications */}
      <NotificationToast
        notifications={notifs.notifications}
        onDismiss={notifs.removeNotification}
        position="top-right"
      />
    </div>
  );
}

export default RiderDashboard;
