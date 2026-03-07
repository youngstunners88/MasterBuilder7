/**
 * NotificationToast Component
 * Displays real-time notifications as toast messages
 */
import React, { useEffect, useState } from 'react';
import { NotificationData, NotificationType } from '../../types/websocket';

// Icons for different notification types
const icons = {
  [NotificationType.SUCCESS]: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  [NotificationType.ERROR]: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  [NotificationType.WARNING]: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  [NotificationType.INFO]: (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  close: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  order: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
    </svg>
  ),
  delivery: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  driver: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 7m0 13V7" />
    </svg>
  ),
};

// Colors for different notification types
const typeColors: Record<NotificationType, { bg: string; border: string; icon: string }> = {
  [NotificationType.SUCCESS]: {
    bg: 'bg-green-50',
    border: 'border-green-400',
    icon: 'text-green-500',
  },
  [NotificationType.ERROR]: {
    bg: 'bg-red-50',
    border: 'border-red-400',
    icon: 'text-red-500',
  },
  [NotificationType.WARNING]: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-400',
    icon: 'text-yellow-500',
  },
  [NotificationType.INFO]: {
    bg: 'bg-blue-50',
    border: 'border-blue-400',
    icon: 'text-blue-500',
  },
};

export interface NotificationToastProps {
  notifications: NotificationData[];
  onDismiss: (id: string) => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center';
  className?: string;
}

export const NotificationToast: React.FC<NotificationToastProps> = ({
  notifications,
  onDismiss,
  position = 'top-right',
  className = '',
}) => {
  // Position classes
  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
    'top-center': 'top-4 left-1/2 -translate-x-1/2',
  };

  return (
    <div
      className={`fixed z-50 flex flex-col gap-3 w-full max-w-sm ${positionClasses[position]} ${className}`}
      style={{ pointerEvents: 'none' }}
    >
      {notifications.map((notification) => (
        <ToastItem
          key={notification.id}
          notification={notification}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  );
};

// Individual toast item component
interface ToastItemProps {
  notification: NotificationData;
  onDismiss: (id: string) => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ notification, onDismiss }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [progress, setProgress] = useState(100);
  const colors = typeColors[notification.type];

  // Get icon based on notification content
  const getIcon = () => {
    if (notification.title.toLowerCase().includes('order')) return icons.order;
    if (notification.title.toLowerCase().includes('deliver')) return icons.delivery;
    if (notification.title.toLowerCase().includes('driver')) return icons.driver;
    return icons[notification.type];
  };

  // Animate in
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 10);
    return () => clearTimeout(timer);
  }, []);

  // Auto-dismiss progress
  useEffect(() => {
    if (!notification.autoDismiss || !notification.dismissAfter) return;

    const duration = notification.dismissAfter;
    const interval = 100; // Update every 100ms
    const decrement = (100 / duration) * interval;

    const progressTimer = setInterval(() => {
      setProgress((prev) => {
        if (prev <= 0) {
          handleDismiss();
          return 0;
        }
        return prev - decrement;
      });
    }, interval);

    return () => clearInterval(progressTimer);
  }, [notification.autoDismiss, notification.dismissAfter]);

  const handleDismiss = () => {
    setIsVisible(false);
    setTimeout(() => onDismiss(notification.id), 300); // Wait for animation
  };

  return (
    <div
      className={`
        pointer-events-auto
        transform transition-all duration-300 ease-out
        ${isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
        ${positionClasses}
      `}
    >
      <div
        className={`
          relative overflow-hidden
          rounded-lg shadow-lg border-l-4
          ${colors.bg} ${colors.border}
          bg-white
        `}
      >
        {/* Progress bar */}
        {notification.autoDismiss && (
          <div
            className={`absolute bottom-0 left-0 h-1 ${colors.bg.replace('bg-', 'bg-opacity-50 bg-').replace('50', '500')}`}
            style={{ width: `${progress}%`, transition: 'width 0.1s linear' }}
          />
        )}

        <div className="p-4">
          <div className="flex items-start gap-3">
            {/* Icon */}
            <div className={`flex-shrink-0 ${colors.icon}`}>
              {getIcon()}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-gray-900">
                {notification.title}
              </h4>
              <p className="text-sm text-gray-600 mt-1">
                {notification.message}
              </p>
              
              {/* Order ID if available */}
              {notification.orderId && (
                <p className="text-xs text-gray-500 mt-1">
                  Order #{notification.orderId.slice(-6).toUpperCase()}
                </p>
              )}

              {/* Timestamp */}
              <p className="text-xs text-gray-400 mt-2">
                {new Date(notification.timestamp).toLocaleTimeString('en-ZA', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </p>
            </div>

            {/* Close button */}
            <button
              onClick={handleDismiss}
              className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
              aria-label="Dismiss notification"
            >
              {icons.close}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Position classes for toast container
const positionClasses = {
  'top-right': '',
  'top-left': '',
  'bottom-right': '',
  'bottom-left': '',
  'top-center': '',
};

// Hook for using notifications
export interface UseNotificationsReturn {
  notifications: NotificationData[];
  addNotification: (notification: Omit<NotificationData, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

export function useNotifications(): UseNotificationsReturn {
  const [notifications, setNotifications] = useState<NotificationData[]>([]);

  const addNotification = React.useCallback(
    (notification: Omit<NotificationData, 'id' | 'timestamp'>) => {
      const newNotification: NotificationData = {
        ...notification,
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now(),
      };

      setNotifications((prev) => [...prev, newNotification]);

      // Auto-remove after dismiss time
      if (notification.autoDismiss && notification.dismissAfter) {
        setTimeout(() => {
          removeNotification(newNotification.id);
        }, notification.dismissAfter);
      }
    },
    []
  );

  const removeNotification = React.useCallback((id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearNotifications = React.useCallback(() => {
    setNotifications([]);
  }, []);

  return {
    notifications,
    addNotification,
    removeNotification,
    clearNotifications,
  };
}

// Predefined notification helpers
export const notificationHelpers = {
  orderCreated: (orderId: string): Omit<NotificationData, 'id' | 'timestamp'> => ({
    type: NotificationType.SUCCESS,
    title: 'Order Placed!',
    message: 'Your order has been placed successfully.',
    orderId,
    autoDismiss: true,
    dismissAfter: 5000,
  }),

  driverAssigned: (orderId: string, driverName?: string): Omit<NotificationData, 'id' | 'timestamp'> => ({
    type: NotificationType.INFO,
    title: 'Driver Assigned',
    message: driverName 
      ? `${driverName} has been assigned to your order.`
      : 'A driver has been assigned to your order.',
    orderId,
    autoDismiss: true,
    dismissAfter: 6000,
  }),

  orderStatusUpdate: (
    orderId: string, 
    status: string
  ): Omit<NotificationData, 'id' | 'timestamp'> => ({
    type: NotificationType.INFO,
    title: 'Order Update',
    message: `Your order status has been updated to: ${status}`,
    orderId,
    autoDismiss: true,
    dismissAfter: 5000,
  }),

  deliveryCompleted: (orderId: string): Omit<NotificationData, 'id' | 'timestamp'> => ({
    type: NotificationType.SUCCESS,
    title: 'Order Delivered!',
    message: 'Your order has been delivered. Enjoy your meal!',
    orderId,
    autoDismiss: true,
    dismissAfter: 8000,
  }),

  deliveryFailed: (orderId: string, reason?: string): Omit<NotificationData, 'id' | 'timestamp'> => ({
    type: NotificationType.ERROR,
    title: 'Delivery Issue',
    message: reason || 'There was an issue with your delivery.',
    orderId,
    autoDismiss: true,
    dismissAfter: 10000,
  }),

  newMessage: (sender: string): Omit<NotificationData, 'id' | 'timestamp'> => ({
    type: NotificationType.INFO,
    title: 'New Message',
    message: `You have a new message from ${sender}.`,
    autoDismiss: true,
    dismissAfter: 5000,
  }),

  connectionError: (): Omit<NotificationData, 'id' | 'timestamp'> => ({
    type: NotificationType.ERROR,
    title: 'Connection Error',
    message: 'Lost connection to server. Reconnecting...',
    autoDismiss: true,
    dismissAfter: 5000,
  }),

  reconnected: (): Omit<NotificationData, 'id' | 'timestamp'> => ({
    type: NotificationType.SUCCESS,
    title: 'Reconnected',
    message: 'Connection restored. You will receive live updates again.',
    autoDismiss: true,
    dismissAfter: 3000,
  }),
};

export default NotificationToast;
