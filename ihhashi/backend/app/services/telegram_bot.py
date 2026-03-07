"""
Telegram Bot Service for iHhashi
Handles customer notifications, support, and order tracking
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

logger = logging.getLogger(__name__)

class TelegramBotService:
    """Telegram bot for iHhashi notifications and support"""
    
    def __init__(self, db=None):
        self.db = db
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.bot = Bot(token=self.token) if self.token else None
        self.app = None
        
    async def start_bot(self):
        """Start the bot application"""
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not set")
            return
            
        self.app = Application.builder().token(self.token).build()
        
        # Register handlers
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("track", self._handle_track))
        self.app.add_handler(CommandHandler("help", self._handle_help))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Start polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
    async def stop_bot(self):
        """Stop the bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
    
    # ============ COMMAND HANDLERS ============
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        telegram_id = update.effective_user.id
        username = update.effective_user.username or "there"
        
        # Check if user is registered
        user = None
        if self.db:
            user = await self.db.users.find_one({"telegram_id": telegram_id})
        
        if user:
            await update.message.reply_text(
                f"Welcome back, {user.get('name', username)}! 👋\n\n"
                "You're connected to iHhashi.\n\n"
                "Commands:\n"
                "/track <order_id> - Track your order\n"
                "/help - Get help\n"
                "/support - Contact support"
            )
        else:
            # Store telegram ID for linking
            await update.message.reply_text(
                f"Hi {username}! 👋\n\n"
                "Welcome to iHhashi - your delivery partner!\n\n"
                "To link your account, please:\n"
                "1. Open the iHhashi app\n"
                "2. Go to Profile > Settings\n"
                "3. Tap 'Link Telegram'\n"
                "4. Enter this code: `{telegram_id}`\n\n"
                "Commands:\n"
                "/track <order_id> - Track your order\n"
                "/help - Get help"
            )
    
    async def _handle_track(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /track command for order tracking"""
        telegram_id = update.effective_user.id
        
        # Get order ID from command
        if not context.args:
            await update.message.reply_text(
                "Please provide an order ID.\n\n"
                "Usage: /track <order_id>\n"
                "Example: /track ORD123456"
            )
            return
        
        order_id = context.args[0]
        
        if not self.db:
            await update.message.reply_text("Tracking unavailable. Please try again later.")
            return
        
        # Find user
        user = await self.db.users.find_one({"telegram_id": telegram_id})
        if not user:
            await update.message.reply_text(
                "Please link your account first. Use /start for instructions."
            )
            return
        
        # Find order
        from bson import ObjectId
        try:
            order = await self.db.orders.find_one({
                "$or": [
                    {"_id": ObjectId(order_id)},
                    {"order_number": order_id}
                ],
                "buyer_id": str(user["_id"])
            })
        except Exception:
            order = await self.db.orders.find_one({
                "order_number": order_id,
                "buyer_id": str(user["_id"])
            })
        
        if not order:
            await update.message.reply_text(
                f"Order `{order_id}` not found. Please check the order ID."
            )
            return
        
        # Format status
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "preparing": "👨‍🍳",
            "ready": "📦",
            "picked_up": "🛵",
            "in_transit": "🚴",
            "delivered": "✅",
            "cancelled": "❌"
        }
        
        status = order.get("status", "pending")
        emoji = status_emoji.get(status, "📦")
        
        message = (
            f"📦 *Order #{order.get('order_number', order_id)}*\n\n"
            f"Status: {emoji} *{status.upper()}*\n"
            f"Total: R{order.get('total', 0):.2f}\n\n"
        )
        
        if order.get("estimated_delivery"):
            message += f"Est. delivery: {order['estimated_delivery']}\n"
        
        if order.get("rider_name"):
            message += f"Rider: {order['rider_name']}\n"
        
        if order.get("rider_phone"):
            message += f"Rider phone: {order['rider_phone']}\n"
        
        await update.message.reply_text(message, parse_mode="Markdown")
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_text(
            "🛵 *iHhashi Help*\n\n"
            "Commands:\n"
            "/start - Link your account\n"
            "/track <order_id> - Track an order\n"
            "/help - Show this message\n\n"
            "Need help? Contact support:\n"
            "📧 support@ihhashi.app\n"
            "📱 WhatsApp: +27 XX XXX XXXX",
            parse_mode="Markdown"
        )
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        # For now, redirect to support
        await update.message.reply_text(
            "Thanks for your message! For faster support:\n\n"
            "📧 Email: support@ihhashi.app\n"
            "📱 WhatsApp: +27 XX XXX XXXX\n\n"
            "Or use /help to see available commands."
        )
    
    # ============ NOTIFICATION METHODS ============
    
    async def send_order_confirmation(
        self,
        telegram_id: int,
        order_number: str,
        total: float,
        items: list,
        estimated_delivery: str = None
    ):
        """Send order confirmation notification"""
        if not self.bot:
            return False
        
        message = (
            f"✅ *Order Confirmed!*\n\n"
            f"Order: #{order_number}\n"
            f"Total: R{total:.2f}\n\n"
            f"Items:\n"
        )
        
        for item in items[:5]:  # Show first 5 items
            message += f"• {item.get('name', 'Item')} x{item.get('quantity', 1)}\n"
        
        if len(items) > 5:
            message += f"... and {len(items) - 5} more\n"
        
        if estimated_delivery:
            message += f"\n⏱ Est. delivery: {estimated_delivery}"
        
        message += "\n\nTrack with: /track " + order_number
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send order confirmation: {e}")
            return False
    
    async def send_delivery_update(
        self,
        telegram_id: int,
        order_number: str,
        status: str,
        message: str,
        rider_name: str = None,
        rider_phone: str = None
    ):
        """Send delivery status update"""
        if not self.bot:
            return False
        
        status_emoji = {
            "confirmed": "✅",
            "preparing": "👨‍🍳",
            "ready": "📦",
            "picked_up": "🛵",
            "in_transit": "🚴",
            "delivered": "✅",
            "cancelled": "❌"
        }
        
        emoji = status_emoji.get(status, "📦")
        
        text = (
            f"{emoji} *Order Update*\n\n"
            f"Order: #{order_number}\n"
            f"Status: {status.upper()}\n"
            f"{message}\n"
        )
        
        if rider_name:
            text += f"\n👤 Rider: {rider_name}"
        if rider_phone:
            text += f"\n📱 {rider_phone}"
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode="Markdown"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send delivery update: {e}")
            return False
    
    async def send_rider_notification(
        self,
        telegram_id: int,
        order_number: str,
        pickup_address: str,
        delivery_address: str,
        fare: float,
        distance_km: float
    ):
        """Send new delivery request to rider"""
        if not self.bot:
            return False
        
        message = (
            f"🛵 *New Delivery Request!*\n\n"
            f"Order: #{order_number}\n"
            f"Distance: {distance_km:.1f} km\n"
            f"Earnings: R{fare:.2f}\n\n"
            f"📍 Pickup:\n{pickup_address}\n\n"
            f"🎯 Delivery:\n{delivery_address}\n\n"
            f"Reply YES to accept or NO to decline."
        )
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send rider notification: {e}")
            return False
    
    async def send_merchant_notification(
        self,
        telegram_id: int,
        order_number: str,
        items: list,
        total: float,
        customer_notes: str = None
    ):
        """Send new order notification to merchant"""
        if not self.bot:
            return False
        
        message = (
            f"📦 *New Order!*\n\n"
            f"Order: #{order_number}\n"
            f"Total: R{total:.2f}\n\n"
            f"Items:\n"
        )
        
        for item in items:
            message += f"• {item.get('name', 'Item')} x{item.get('quantity', 1)}\n"
        
        if customer_notes:
            message += f"\n📝 Notes: {customer_notes}"
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send merchant notification: {e}")
            return False


# Singleton instance
_telegram_service = None

def get_telegram_service(db=None):
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramBotService(db)
    return _telegram_service
