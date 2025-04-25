from fastapi import WebSocket, Depends
from typing import List, Dict
import redis.asyncio as redis
import json
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.models.models import Notification

REDIS_URL = "redis://localhost:6379"  # Replace with your Redis URL


class WebSocketManager:
    def __init__(self):
        self.redis = redis.Redis.from_url(REDIS_URL)
        self.pubsub = self.redis.pubsub()
        # user_id: [websocket]
        self.active_connections: Dict[UUID, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, company_id: UUID, user_id: UUID):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        # Subscribe to company-specific channel
        await self.pubsub.subscribe(str(company_id))
        print(f"Client {user_id} connected to company {company_id}")

    def disconnect(self, websocket: WebSocket, company_id: UUID, user_id: UUID):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        # Unsubscribe from company-specific channel
        self.redis.unsubscribe(str(company_id))
        print(f"Client {user_id} disconnected from company {company_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, company_id: UUID, message: str):
        """Publish message to Redis channel for the company."""
        await self.redis.publish(str(company_id), message)

    async def handle_message(self, company_id: UUID, user_id: UUID, message: str):
        """Process incoming messages (e.g., save to DB, trigger actions)."""
        print(
            f"Received message from user {user_id} in company {company_id}: {message}"
        )
        # Example: Save message to database (omitted for brevity)
        # await save_message_to_db(company_id, user_id, message)

    async def send_notification_to_company(
        self, company_id: UUID, message: str, db: AsyncSession
    ):
        """Send a notification to all connected users in a company."""
        await self.broadcast(company_id, message)
        # Save notification to the database
        notification = Notification(company_id=company_id, message=message)
        db.add(notification)
        await db.commit()

    async def listen_for_messages(self):
        """Listen for messages on Redis Pub/Sub channels and forward to clients."""
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                company_id = message["channel"].decode("utf-8")
                data = message["data"].decode("utf-8")
                # Send to all connected websockets in the company
                await self.distribute_message(company_id, data)

    async def distribute_message(self, company_id: str, message: str):
        """Distribute a message to all connected websockets in a company."""
        for user_id, connections in self.active_connections.items():
            for websocket in connections:
                try:
                    await websocket.send_text(f"Company {company_id} says: {message}")
                except Exception as e:
                    print(f"Error sending message to websocket: {e}")

    async def notify_new_order(
        self, company_id: UUID, room_or_table_number: str, db: AsyncSession
    ):
        """Notify the company about a new order."""
        message = f"New order from: {room_or_table_number}"
        await self.send_notification_to_company(company_id, message, db)

    async def notify_order_status_update(
        self, user_id: UUID, order_id: UUID, status: str, db: AsyncSession
    ):
        """Notify the guest about an order status update."""
        message = f"Your order with ID: {order_id} has been updated to status: {status}"
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_text(message)
                    # Save notification to the database
                    notification = Notification(
                        user_id=user_id, company_id="", message=message
                    )
                    db.add(notification)
                    await db.commit()
                except Exception as e:
                    print(f"Error sending message to websocket: {e}")


manager = WebSocketManager()
