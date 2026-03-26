import asyncio
import websockets
import json

async def test():
    uri = "ws://127.0.0.1:8000/ws/tutor"

    async with websockets.connect(uri) as ws:

        # send message
        await ws.send(json.dumps({
            "session_id": "test123",
            "message": "Hi"
        }))

        response = await ws.recv()
        print("Response:", response)

asyncio.run(test())