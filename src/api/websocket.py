from fastapi import APIRouter
router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/chat/{user_id}")
async def websocket_chat_endpoint(websocket, user_id: str):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "user_id": user_id})
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "data": data})
    except:
        pass

@router.websocket("/ws/avatar/{user_id}")
async def websocket_avatar_endpoint(websocket, user_id: str):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "user_id": user_id})
