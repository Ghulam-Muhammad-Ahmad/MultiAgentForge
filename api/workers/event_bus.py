"""Synchronous Redis pub/sub publisher for use inside Celery workers.

FastAPI subscribes to the same channel via redis.asyncio and forwards
events to the in-process WebSocket ConnectionManager.
"""
import json
import redis as _redis
from config import settings

CHANNEL = "agent_events"


def publish(event: str, data: dict) -> None:
    r = _redis.from_url(settings.redis_url, decode_responses=True)
    try:
        r.publish(CHANNEL, json.dumps({"event": event, "data": data}))
    finally:
        r.close()
