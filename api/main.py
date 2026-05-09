import asyncio
import json
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from ws import manager
from workers.event_bus import CHANNEL
from routers import projects, requirements, board, tickets, agents, commands, preview, delivery


async def _redis_event_listener():
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    await manager.broadcast(payload["event"], payload["data"])
                except Exception:
                    pass
    finally:
        await r.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_redis_event_listener())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Multi-Agent Builder API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3004"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(requirements.router)
app.include_router(board.router)
app.include_router(tickets.router)
app.include_router(agents.router)
app.include_router(commands.router)
app.include_router(preview.router)
app.include_router(delivery.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/health")
async def health():
    return {"status": "ok"}
