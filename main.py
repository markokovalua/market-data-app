import asyncio
import csv
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import aiofiles

HISTORICAL_FILE = "historical_data.csv"
LIVE_FILE = "live_data.csv"

app = FastAPI()

class ClientConnection:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.mode = "live"
        self.task: asyncio.Task | None = None

clients: dict[WebSocket, ClientConnection] = {}

async def read_historical():
    async with aiofiles.open(HISTORICAL_FILE, mode='r') as f:
        content = await f.read()
        reader = csv.DictReader(content.splitlines())
        rows = list(reader)
        for row in rows:
            ts = datetime.fromisoformat(row["timestamp"])
            latency = timedelta(milliseconds=float(row["latency"]))
            row["effective_time"] = (ts + latency).isoformat()
        rows.sort(key=lambda r: r["effective_time"])
        for row in rows:
            row["type"] = "historical"
            yield row
            await asyncio.sleep(0.001)

async def read_live():
    async with aiofiles.open(LIVE_FILE, mode='r') as f:
        content = await f.read()
        reader = csv.DictReader(content.splitlines())
        for row in reader:
            row["type"] = "live"
            yield row
            await asyncio.sleep(0.001)

async def stream_client(client: ClientConnection):
    try:
        if client.mode == "live":
            async for row in read_live():
                await client.websocket.send_json(row)
        elif client.mode == "historical":
            async for row in read_historical():
                await client.websocket.send_json(row)
    except asyncio.CancelledError:
        print(f"Client stream cancelled ({client.mode})")
    except WebSocketDisconnect:
        print("Client disconnected during stream")
    except Exception as e:
        print(f"Error sending data to client: {e}")

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    client = ClientConnection(ws)
    clients[ws] = client
    client.task = asyncio.create_task(stream_client(client))

    try:
        while True:
            msg = await ws.receive_json()
            mode = msg.get("mode")
            if mode in ["live", "historical"]:
                if client.task:
                    client.task.cancel()
                client.mode = mode
                client.task = asyncio.create_task(stream_client(client))
    except WebSocketDisconnect:
        await disconnect_client(ws)

async def disconnect_client(ws: WebSocket):
    client = clients.pop(ws, None)
    if client and client.task:
        client.task.cancel()
    print("Client disconnected")
