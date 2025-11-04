import asyncio
import json
import os
import logging

try:
    # redis-py v4+ provides asyncio support under redis.asyncio
    from redis.asyncio import Redis
except Exception:
    Redis = None

from .ws_manager import manager

logger = logging.getLogger(__name__)
CHANNEL = os.getenv("WS_REDIS_CHANNEL", "messages_events")


class RedisBridge:
    def __init__(self):
        self.redis = None
        self._task = None

    async def init(self):
        if Redis is None:
            logger.warning("redis.asyncio not available; Redis bridge disabled")
            return
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = Redis.from_url(url, decode_responses=True)
        # Start subscriber loop
        self._task = asyncio.create_task(self._subscriber_loop())

    async def close(self):
        if self._task:
            self._task.cancel()
        if self.redis:
            await self.redis.close()

    async def publish(self, payload: dict):
        if not self.redis:
            # No-op when redis not configured
            return
        try:
            await self.redis.publish(CHANNEL, json.dumps(payload, default=str))
        except Exception as e:
            logger.exception("Failed to publish to Redis: %s", e)

    async def _subscriber_loop(self):
        if not self.redis:
            return
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        logger.info(f"Subscribed to Redis channel: {CHANNEL}")
        try:
            async for message in pubsub.listen():
                if message is None:
                    continue
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                try:
                    payload = json.loads(data)
                except Exception:
                    logger.exception("Invalid JSON from Redis: %s", data)
                    continue

                # Route to connected clients via manager
                receiver_id = payload.get("receiver_id") or payload.get("user_id")
                if receiver_id:
                    await manager.send_personal_message(receiver_id, payload)
                else:
                    # broadcast if no specific receiver
                    await manager.broadcast(payload)
        except asyncio.CancelledError:
            logger.info("Redis subscriber loop cancelled")
        except Exception:
            logger.exception("Error in redis subscriber loop")


bridge = RedisBridge()
