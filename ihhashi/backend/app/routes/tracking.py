"""
Real-time tracking WebSocket server
Enables live order tracking for customers and riders
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Optional
from datetime import datetime
import json
import asyncio

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time tracking"""
    
    def __init__(self):
        # order_id -> set of websocket connections
        self.order_connections: Dict[str, Set[WebSocket]] = {}
        # rider_id -> websocket connection
        self.rider_connections: Dict[str, WebSocket] = {}
        # user_id -> websocket connection
        self.user_connections: Dict[str, WebSocket] = {}
    
    async def connect_order(self, websocket: WebSocket, order_id: str):
        """Connect to order tracking room"""
        await websocket.accept()
        if order_id not in self.order_connections:
            self.order_connections[order_id] = set()
        self.order_connections[order_id].add(websocket)
        print(f"📱 Client connected to order {order_id}")
    
    async def connect_rider(self, websocket: WebSocket, rider_id: str):
        """Connect rider for location updates"""
        await websocket.accept()
        self.rider_connections[rider_id] = websocket
        print(f"🚴 Rider {rider_id} connected")
    
    async def connect_user(self, websocket: WebSocket, user_id: str):
        """Connect user for notifications"""
        await websocket.accept()
        self.user_connections[user_id] = websocket
        print(f"👤 User {user_id} connected")
    
    def disconnect_order(self, websocket: WebSocket, order_id: str):
        """Disconnect from order tracking"""
        if order_id in self.order_connections:
            self.order_connections[order_id].discard(websocket)
            if not self.order_connections[order_id]:
                del self.order_connections[order_id]
    
    def disconnect_rider(self, rider_id: str):
        """Disconnect rider"""
        if rider_id in self.rider_connections:
            del self.rider_connections[rider_id]
    
    def disconnect_user(self, user_id: str):
        """Disconnect user"""
        if user_id in self.user_connections:
            del self.user_connections[user_id]
    
    async def broadcast_to_order(self, order_id: str, message: dict):
        """Broadcast message to all connections tracking an order"""
        if order_id not in self.order_connections:
            return
        
        dead_connections = set()
        for connection in self.order_connections[order_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        
        # Clean up dead connections
        for conn in dead_connections:
            self.order_connections[order_id].discard(conn)
    
    async def send_to_rider(self, rider_id: str, message: dict):
        """Send message to specific rider"""
        if rider_id in self.rider_connections:
            try:
                await self.rider_connections[rider_id].send_json(message)
            except Exception:
                self.disconnect_rider(rider_id)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user"""
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_json(message)
            except Exception:
                self.disconnect_user(user_id)
    
    async def update_rider_location(self, rider_id: str, lat: float, lng: float, order_id: Optional[str] = None):
        """Update rider location and broadcast to order tracking"""
        location_update = {
            "type": "rider_location",
            "rider_id": rider_id,
            "lat": lat,
            "lng": lng,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to order if specified
        if order_id:
            await self.broadcast_to_order(order_id, location_update)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/track/{order_id}")
async def track_order_websocket(websocket: WebSocket, order_id: str):
    """
    WebSocket endpoint for order tracking
    
    Clients connect to receive real-time updates:
    - Order status changes
    - Rider location updates
    - Estimated arrival changes
    """
    await manager.connect_order(websocket, order_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "order_id": order_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle ping/pong for keepalive
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                # Client can request status refresh
                elif message.get("type") == "get_status":
                    # Fetch current order status from database
                    from app.database import get_collection
                    orders_col = get_collection("orders")
                    order = await orders_col.find_one({"id": order_id})
                    
                    if order:
                        await websocket.send_json({
                            "type": "status_update",
                            "status": order.get("status"),
                            "rider_location": {
                                "lat": order.get("rider_lat"),
                                "lng": order.get("rider_lng")
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        })
            
            except json.JSONDecodeError:
                # Ignore invalid JSON
                pass
    
    except WebSocketDisconnect:
        manager.disconnect_order(websocket, order_id)
        print(f"📱 Client disconnected from order {order_id}")


@router.websocket("/rider/{rider_id}")
async def rider_websocket(websocket: WebSocket, rider_id: str):
    """
    WebSocket endpoint for rider
    
    Riders connect to:
    - Send location updates
    - Receive new order notifications
    - Receive order status changes
    """
    await manager.connect_rider(websocket, rider_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "rider_id": rider_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle location updates
                if message.get("type") == "location_update":
                    lat = message.get("lat")
                    lng = message.get("lng")
                    order_id = message.get("order_id")
                    
                    if lat and lng:
                        # Update rider location in database
                        from app.database import get_collection
                        riders_col = get_collection("riders")
                        await riders_col.update_one(
                            {"id": rider_id},
                            {
                                "$set": {
                                    "current_lat": lat,
                                    "current_lng": lng,
                                    "last_location_update": datetime.utcnow().isoformat()
                                }
                            }
                        )
                        
                        # Broadcast to order tracking
                        if order_id:
                            await manager.update_rider_location(rider_id, lat, lng, order_id)
                        
                        await websocket.send_json({
                            "type": "location_ack",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                
                # Handle status updates
                elif message.get("type") == "status_update":
                    status = message.get("status")
                    if status:
                        from app.database import get_collection
                        riders_col = get_collection("riders")
                        await riders_col.update_one(
                            {"id": rider_id},
                            {"$set": {"status": status}}
                        )
                        
                        await websocket.send_json({
                            "type": "status_ack",
                            "status": status
                        })
            
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        manager.disconnect_rider(rider_id)
        print(f"🚴 Rider {rider_id} disconnected")


@router.websocket("/user/{user_id}")
async def user_websocket(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for user notifications
    
    Users connect to receive:
    - Order status changes
    - New order notifications (for merchants)
    - Chat messages
    """
    await manager.connect_user(websocket, user_id)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        manager.disconnect_user(user_id)
        print(f"👤 User {user_id} disconnected")


# API endpoint to broadcast order update (called by other services)
async def broadcast_order_update(order_id: str, update_type: str, data: dict):
    """Broadcast order update to all tracking clients"""
    message = {
        "type": update_type,
        "order_id": order_id,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.broadcast_to_order(order_id, message)


async def notify_rider_new_order(rider_id: str, order_data: dict):
    """Notify rider about new available order"""
    message = {
        "type": "new_order",
        "order": order_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_to_rider(rider_id, message)


async def notify_user_order_update(user_id: str, order_id: str, status: str):
    """Notify user about order status change"""
    message = {
        "type": "order_update",
        "order_id": order_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_to_user(user_id, message)


# Expose manager for use in other modules
def get_manager():
    return manager
