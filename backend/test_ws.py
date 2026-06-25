import asyncio
import websockets


async def main():

    async with websockets.connect(
        "ws://localhost:8000/api/jee/live-tutor"
    ) as ws:

        await ws.send(
            "U6WIWSmQoHDv1aZXTCtE"
        )

        await ws.send(
            "Why do we find Median?"
        )

        response = await ws.recv()

        print(response)

asyncio.run(main())