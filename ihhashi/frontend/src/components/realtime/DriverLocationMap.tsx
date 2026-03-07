/**
 * DriverLocationMap Component
 * Displays driver's real-time location on a map
 * Note: This is a visual representation. For production, integrate with Google Maps or Mapbox
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { LocationData } from '../../types/websocket';

// Icons
const icons = {
  driver: (
    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zM7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 2.88-2.88 7.19-5 9.88C9.92 16.21 7 11.85 7 9z"/>
      <circle cx="12" cy="9" r="2.5"/>
    </svg>
  ),
  destination: (
    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
    </svg>
  ),
  restaurant: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
    </svg>
  ),
  navigation: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
  speed: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  time: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  arrow: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  ),
};

export interface DriverLocationMapProps {
  driverLocation: LocationData;
  driverName?: string;
  driverHeading?: number;
  destinationLocation?: LocationData;
  restaurantLocation?: LocationData;
  className?: string;
  height?: string | number;
  showInfo?: boolean;
  estimatedArrival?: string;
  orderStatus?: string;
}

export const DriverLocationMap: React.FC<DriverLocationMapProps> = ({
  driverLocation,
  driverName,
  driverHeading = 0,
  destinationLocation,
  restaurantLocation,
  className = '',
  height = 300,
  showInfo = true,
  estimatedArrival,
  orderStatus,
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [center, setCenter] = useState({ lat: driverLocation.latitude, lng: driverLocation.longitude });

  // Update center when driver location changes (smooth panning)
  useEffect(() => {
    setCenter({ lat: driverLocation.latitude, lng: driverLocation.longitude });
  }, [driverLocation.latitude, driverLocation.longitude]);

  // Simulate map loading
  useEffect(() => {
    const timer = setTimeout(() => setMapLoaded(true), 500);
    return () => clearTimeout(timer);
  }, []);

  // Calculate relative position for visual map
  const getRelativePosition = useCallback((lat: number, lng: number) => {
    const latDiff = lat - center.lat;
    const lngDiff = lng - center.lng;
    // Scale for visual representation (not accurate for large distances)
    const scale = 100000;
    return {
      x: 50 + lngDiff * scale,
      y: 50 - latDiff * scale,
    };
  }, [center]);

  const driverPos = getRelativePosition(driverLocation.latitude, driverLocation.longitude);
  const destPos = destinationLocation ? getRelativePosition(destinationLocation.latitude, destinationLocation.longitude) : null;
  const restPos = restaurantLocation ? getRelativePosition(restaurantLocation.latitude, restaurantLocation.longitude) : null;

  // Calculate bearing (simplified)
  const getBearing = useCallback(() => {
    if (driverHeading !== undefined && driverHeading !== null) {
      return driverHeading;
    }
    // Calculate bearing from driver to destination if available
    if (destinationLocation) {
      const y = Math.sin(destinationLocation.longitude - driverLocation.longitude) * 
                Math.cos(destinationLocation.latitude);
      const x = Math.cos(driverLocation.latitude) * Math.sin(destinationLocation.latitude) -
                Math.sin(driverLocation.latitude) * Math.cos(destinationLocation.latitude) * 
                Math.cos(destinationLocation.longitude - driverLocation.longitude);
      const bearing = Math.atan2(y, x) * (180 / Math.PI);
      return (bearing + 360) % 360;
    }
    return 0;
  }, [driverHeading, destinationLocation, driverLocation]);

  // Calculate estimated distance (mock calculation)
  const calculateDistance = useCallback(() => {
    if (!destinationLocation) return null;
    // Haversine formula approximation
    const R = 6371; // Earth's radius in km
    const dLat = (destinationLocation.latitude - driverLocation.latitude) * Math.PI / 180;
    const dLon = (destinationLocation.longitude - driverLocation.longitude) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(driverLocation.latitude * Math.PI / 180) * 
              Math.cos(destinationLocation.latitude * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return Math.round(R * c * 10) / 10; // Round to 1 decimal place
  }, [driverLocation, destinationLocation]);

  const distance = calculateDistance();
  const bearing = getBearing();

  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden ${className}`}>
      {/* Map Header */}
      {showInfo && (
        <div className="px-4 py-3 bg-gray-800 text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-sm font-medium">Live Tracking</span>
          </div>
          {estimatedArrival && (
            <div className="flex items-center gap-1 text-sm">
              {icons.time}
              <span>ETA: {estimatedArrival}</span>
            </div>
          )}
        </div>
      )}

      {/* Map Container */}
      <div 
        ref={mapRef}
        className="relative bg-gray-100 overflow-hidden"
        style={{ height: typeof height === 'number' ? `${height}px` : height }}
      >
        {/* Loading State */}
        {!mapLoaded && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500" />
          </div>
        )}

        {/* Map Background (Grid Pattern) */}
        <div 
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: `
              linear-gradient(to right, #cbd5e1 1px, transparent 1px),
              linear-gradient(to bottom, #cbd5e1 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
          }}
        />

        {/* Map Content */}
        {mapLoaded && (
          <>
            {/* Restaurant Marker */}
            {restPos && orderStatus && ['pending', 'confirmed', 'preparing'].includes(orderStatus) && (
              <div
                className="absolute transform -translate-x-1/2 -translate-y-1/2 z-10"
                style={{ left: `${restPos.x}%`, top: `${restPos.y}%` }}
              >
                <div className="relative">
                  <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center text-white shadow-lg border-2 border-white">
                    {icons.restaurant}
                  </div>
                  <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 translate-y-full">
                    <span className="px-2 py-1 bg-gray-800 text-white text-xs rounded whitespace-nowrap">
                      Restaurant
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Destination Marker */}
            {destPos && (
              <div
                className="absolute transform -translate-x-1/2 -translate-y-1/2 z-10"
                style={{ left: `${destPos.x}%`, top: `${destPos.y}%` }}
              >
                <div className="relative">
                  <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center text-white shadow-lg border-2 border-white">
                    {icons.destination}
                  </div>
                  <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 translate-y-full">
                    <span className="px-2 py-1 bg-gray-800 text-white text-xs rounded whitespace-nowrap">
                      Your Location
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Driver Marker */}
            <div
              className="absolute transform -translate-x-1/2 -translate-y-1/2 z-20 transition-all duration-1000 ease-out"
              style={{ 
                left: `${driverPos.x}%`, 
                top: `${driverPos.y}%`,
              }}
            >
              <div className="relative">
                {/* Pulse Effect */}
                <div className="absolute inset-0 w-12 h-12 -m-1.5">
                  <div className="w-full h-full bg-orange-500 rounded-full animate-ping opacity-30" />
                </div>
                
                {/* Driver Icon */}
                <div 
                  className="w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center text-white shadow-lg border-3 border-white relative"
                  style={{ transform: `rotate(${bearing}deg)` }}
                >
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2L4 12h16L12 2zm0 4.5L15.5 10h-7L12 6.5z"/>
                  </svg>
                </div>

                {/* Driver Label */}
                {driverName && (
                  <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 -translate-y-full">
                    <span className="px-2 py-1 bg-gray-800 text-white text-xs rounded whitespace-nowrap">
                      {driverName}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Route Line (Visual Only) */}
            {destPos && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none">
                <line
                  x1={`${driverPos.x}%`}
                  y1={`${driverPos.y}%`}
                  x2={`${destPos.x}%`}
                  y2={`${destPos.y}%`}
                  stroke="#f97316"
                  strokeWidth="3"
                  strokeDasharray="8,4"
                  className="opacity-60"
                />
              </svg>
            )}

            {/* Map Controls */}
            <div className="absolute bottom-4 right-4 flex flex-col gap-2">
              <button
                onClick={() => setCenter({ lat: driverLocation.latitude, lng: driverLocation.longitude })}
                className="w-10 h-10 bg-white rounded-lg shadow-md flex items-center justify-center text-gray-600 hover:bg-gray-50 transition-colors"
                title="Center on driver"
              >
                {icons.navigation}
              </button>
            </div>

            {/* Coordinates Display */}
            <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-2 text-xs text-gray-600 shadow-sm">
              <div className="font-mono">
                {driverLocation.latitude.toFixed(6)}, {driverLocation.longitude.toFixed(6)}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Info Panel */}
      {showInfo && (
        <div className="px-4 py-3 bg-white border-t border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {driverName && (
                <div>
                  <p className="text-xs text-gray-500">Driver</p>
                  <p className="text-sm font-medium text-gray-900">{driverName}</p>
                </div>
              )}
              
              {distance !== null && (
                <div>
                  <p className="text-xs text-gray-500">Distance</p>
                  <p className="text-sm font-medium text-gray-900">{distance} km</p>
                </div>
              )}

              {driverLocation.speed !== undefined && driverLocation.speed !== null && (
                <div>
                  <p className="text-xs text-gray-500">Speed</p>
                  <div className="flex items-center gap-1">
                    {icons.speed}
                    <p className="text-sm font-medium text-gray-900">
                      {driverLocation.speed.toFixed(1)} km/h
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Last Updated */}
            <div className="text-right">
              <p className="text-xs text-gray-500">Last Update</p>
              <p className="text-xs text-gray-400">
                {driverLocation.last_updated 
                  ? new Date(driverLocation.last_updated).toLocaleTimeString('en-ZA')
                  : 'Just now'
                }
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Compact version for small spaces
export interface CompactDriverMapProps {
  driverLocation: LocationData;
  className?: string;
}

export const CompactDriverMap: React.FC<CompactDriverMapProps> = ({
  driverLocation,
  className = '',
}) => {
  return (
    <div className={`bg-gray-100 rounded-lg p-3 ${className}`}>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center text-white">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
          </svg>
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900">Driver Location</p>
          <p className="text-xs text-gray-500">
            {driverLocation.latitude.toFixed(4)}, {driverLocation.longitude.toFixed(4)}
          </p>
        </div>
        <div className="flex items-center gap-1 text-green-600">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-xs font-medium">Live</span>
        </div>
      </div>
    </div>
  );
};

export default DriverLocationMap;
