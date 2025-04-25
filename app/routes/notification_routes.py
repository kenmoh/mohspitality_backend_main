from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from app.models.models import User
from app.services.notification_service import manager
from uuid import UUID
from app.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession  # Assuming you have this utility
from typing import Optional

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.websocket("/ws/{company_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    company_id: UUID,
    current_user: User,  # Expect the token as a query parameter
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = ""
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Fetch user roles and company info from the database (example)
        # result = await db.execute(select(User).where(User.id == user_id))
        # user = result.scalar_one_or_none()
        # if not user or user.company_id != company_id:
        #     raise HTTPException(status_code=403, detail="Unauthorized")

        # Pass company_id and user_id
        await manager.connect(websocket, company_id, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                # Process the data or trigger actions based on the message
                await manager.handle_message(company_id, user_id, data)
                # Example: Send a message to the user
                await manager.send_personal_message(f"You wrote: {data}", websocket)
        except WebSocketDisconnect:
            manager.disconnect(websocket, company_id, user_id)
            print(f"Client {company_id} disconnected")
    except HTTPException as e:
        await websocket.close(code=e.status_code)
    except Exception as e:
        await websocket.close(code=1011)  # Internal Error
        print(f"WebSocket error: {e}")


@router.post("/new_order/{company_id}/{order_id}")
async def notify_new_order_route(company_id: UUID, order_id: UUID):
    """Route to trigger a new order notification to the company."""
    await manager.notify_new_order(company_id=company_id, order_id=order_id)
    return {"message": f"New order notification sent to company {company_id}"}


@router.post("/order_status_update/{user_id}/{order_id}/{status}")
async def notify_order_status_update_route(user_id: UUID, order_id: UUID, status: str):
    """Route to trigger an order status update notification to the guest."""
    await manager.notify_order_status_update(
        user_id=user_id, order_id=order_id, status=status
    )
    return {"message": f"Order status update sent to user {user_id}"}
