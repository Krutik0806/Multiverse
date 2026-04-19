"""
Upstash Redis REST API client (async, no standard Redis protocol needed).
Uses httpx to call Upstash REST endpoints for all Redis operations.
"""
import httpx
from config import UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN


class UpstashRedis:
    def __init__(self):
        self.url = UPSTASH_REDIS_REST_URL.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}",
            "Content-Type": "application/json",
        }

    async def _execute(self, *args):
        """Execute a single Redis command via REST API."""
        command = [str(a) for a in args]
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(self.url, json=command, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("result")

    async def _pipeline(self, commands: list):
        """Execute multiple Redis commands in a pipeline."""
        payload = [[str(a) for a in cmd] for cmd in commands]
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.url}/pipeline", json=payload, headers=self.headers
            )
            resp.raise_for_status()
            return [item.get("result") for item in resp.json()]

    # ── Core ops ──────────────────────────────────────────────
    async def set(self, key: str, value, ex: int = None):
        if ex:
            return await self._execute("SET", key, value, "EX", ex)
        return await self._execute("SET", key, value)

    async def get(self, key: str):
        return await self._execute("GET", key)

    async def delete(self, *keys):
        return await self._execute("DEL", *keys)

    async def exists(self, *keys):
        result = await self._execute("EXISTS", *keys)
        return int(result) if result else 0

    async def ttl(self, key: str) -> int:
        result = await self._execute("TTL", key)
        return int(result) if result is not None else -2

    async def incr(self, key: str) -> int:
        result = await self._execute("INCR", key)
        return int(result)

    async def expire(self, key: str, seconds: int):
        return await self._execute("EXPIRE", key, seconds)

    async def setex(self, key: str, seconds: int, value):
        return await self._execute("SET", key, value, "EX", seconds)

    # ── Cooldown helpers ───────────────────────────────────────
    async def set_cooldown(self, user_id: int, cooldown_type: str, seconds: int):
        """Set a cooldown that expires after `seconds`."""
        key = f"cd:{user_id}:{cooldown_type}"
        await self.setex(key, seconds, "1")

    async def get_cooldown(self, user_id: int, cooldown_type: str) -> int:
        """Returns remaining seconds, or 0 if no cooldown."""
        key = f"cd:{user_id}:{cooldown_type}"
        result = await self.ttl(key)
        return max(0, result) if result > 0 else 0

    # ── Rate limiting ──────────────────────────────────────────
    async def rate_limit(self, user_id: int, command: str, window: int = 3) -> bool:
        """Returns True if rate-limited (too many calls), False if OK."""
        key = f"rl:{user_id}:{command}"
        count = await self.incr(key)
        if count == 1:
            await self.expire(key, window)
        return count > 1

    # ── Session state ──────────────────────────────────────────
    async def set_session(self, user_id: int, data: str, ex: int = 300):
        """Store session JSON string."""
        await self.setex(f"sess:{user_id}", ex, data)

    async def get_session(self, user_id: int) -> str | None:
        return await self.get(f"sess:{user_id}")

    async def delete_session(self, user_id: int):
        await self.delete(f"sess:{user_id}")

    # ── Stamina regen tracking ─────────────────────────────────
    async def set_stamina_regen(self, user_id: int, seconds: int = 1800):
        """Mark when next stamina tick is due."""
        key = f"stam:{user_id}"
        await self.setex(key, seconds, "1")

    async def stamina_regen_ready(self, user_id: int) -> bool:
        key = f"stam:{user_id}"
        result = await self.ttl(key)
        return result <= 0  # expired = ready for regen


redis = UpstashRedis()
