#!/usr/bin/env python3
import asyncio
import json
import threading
import time

import requests
import websockets

WS_URI = "ws://localhost:8000/ws/tutor?session_id=test-sess-1&grade=10&exam=cbse&mode=class"
API_URL = "http://localhost:8000/api/tutor/ask"

async def ws_listener():
    print("Connecting to", WS_URI)
    async with websockets.connect(WS_URI) as ws:
        print("Connected. Listening for messages...")
        try:
            async for message in ws:
                try:
                    payload = json.loads(message)
                    print("WS MESSAGE:", json.dumps(payload, indent=2))
                except Exception:
                    print("WS RAW:", message)
        except websockets.exceptions.ConnectionClosed as e:
            print("WebSocket closed", e)

def trigger_actions():
    time.sleep(1.5)
    body = {"session_id": "test-sess-1", "mode": "class", "input": {"action": "start"}}
    try:
        r = requests.post(API_URL, json=body, timeout=10)
        print("POST start ->", r.status_code)
    except Exception as e:
        print("POST start failed:", e)
    time.sleep(2)
    body["input"]["action"] = "next"
    try:
        r = requests.post(API_URL, json=body, timeout=10)
        print("POST next ->", r.status_code)
    except Exception as e:
        print("POST next failed:", e)

if __name__ == "__main__":
    t = threading.Thread(target=trigger_actions, daemon=True)
    t.start()
    asyncio.run(ws_listener())
