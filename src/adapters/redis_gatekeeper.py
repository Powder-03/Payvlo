"""Upstash Redis & In-Memory Gatekeeper Adapter.

Clean Architecture layer: Adapters.
Implements IGatekeeper port using atomic Lua scripts for sub-ms spend cap
and 24-hour idempotency key replay defense.
"""
import time
import threading
from typing import Tuple, Optional, Dict, Any
import logging

try:
    import redis
except ImportError:
    redis = None

from ..domain.gatekeeper import IGatekeeper

logger = logging.getLogger("Gatekeeper")

# ==========================================
# Atomic Lua Scripts for Redis
# ==========================================
LUA_SPEND_CAP_CHECK = """
-- KEYS[1]: merchant_spend_key (e.g., "spend:merchant:{merchant_id}:{date}")
-- KEYS[2]: user_spend_key (e.g., "spend:user:{user_id}:{date}")
-- ARGV[1]: amount (e.g., "499.50")
-- ARGV[2]: user_budget (e.g., "1000.00")
-- ARGV[3]: merchant_daily_cap (e.g., "100000.00")

local amount = tonumber(ARGV[1])
local user_budget = tonumber(ARGV[2])
local merchant_cap = tonumber(ARGV[3])

local user_spend = tonumber(redis.call('get', KEYS[2]) or '0')
local merchant_spend = tonumber(redis.call('get', KEYS[1]) or '0')

if (amount > user_budget) then
    return {0, "EXCEEDS_SINGLE_TX_USER_BUDGET", user_spend, merchant_spend}
end

if (merchant_spend + amount > merchant_cap) then
    return {0, "EXCEEDS_MERCHANT_DAILY_CAP", user_spend, merchant_spend}
end

-- Atomic Increment and TTL refresh (24 hours)
local new_user_spend = redis.call('incrbyfloat', KEYS[2], amount)
local new_merchant_spend = redis.call('incrbyfloat', KEYS[1], amount)
redis.call('expire', KEYS[2], 86400)
redis.call('expire', KEYS[1], 86400)

return {1, "APPROVED", new_user_spend, new_merchant_spend}
"""

LUA_IDEMPOTENCY_ACQUIRE = """
-- KEYS[1]: idempotency_key (e.g., "idempotency:{key}")
-- ARGV[1]: payload (cached order JSON or empty string on lock)
-- ARGV[2]: ttl_seconds (e.g., 86400)

local existing = redis.call('get', KEYS[1])
local incoming_payload = ARGV[1]

if incoming_payload and incoming_payload ~= "" then
    -- Updating cached result after successful transaction
    redis.call('setex', KEYS[1], tonumber(ARGV[2]), incoming_payload)
    return {1, "UPDATED"}
end

if existing and existing ~= "" then
    return {0, existing}
end

if existing then
    -- Lock exists but payload not yet populated
    return {0, ""}
end

-- New lock acquisition
redis.call('setex', KEYS[1], tonumber(ARGV[2]), "")
return {1, "ACQUIRED"}
"""


class RedisGatekeeperAdapter(IGatekeeper):
    """Adapter for Upstash Redis or standard Redis instance."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self._memory_idempotency: Dict[str, Dict[str, Any]] = {}
        self._memory_spend_merchant: Dict[str, float] = {}
        self._memory_spend_user: Dict[str, float] = {}
        self._lock = threading.Lock()

        if redis_url and redis:
            try:
                self.redis_client = redis.from_url(
                    redis_url, decode_responses=True, socket_timeout=3.0
                )
                self.redis_client.ping()
                logger.info(f"Connected to Redis Gatekeeper at {redis_url[:18]}...")
            except Exception as e:
                logger.warning(
                    f"Could not connect to Redis ({e}). Falling back to Atomic In-Memory Gatekeeper."
                )
                self.redis_client = None
        else:
            logger.info("No Redis URL configured. Using Atomic In-Memory Gatekeeper.")

    def check_and_acquire_idempotency(
        self, idempotency_key: str, payload: str, ttl_seconds: int = 86400
    ) -> Tuple[bool, Optional[str]]:
        """Atomically checks if key was processed.

        Returns: (is_new, cached_payload_if_replayed)
        """
        redis_key = f"idempotency:{idempotency_key}"

        if self.redis_client:
            try:
                res = self.redis_client.eval(
                    LUA_IDEMPOTENCY_ACQUIRE, 1, redis_key, payload or "", ttl_seconds
                )
                is_new = bool(res[0] == 1)
                cached = None if is_new or not res[1] or res[1] == "" else res[1]
                return is_new, cached
            except Exception as e:
                logger.warning(f"Redis idempotency error ({e}), falling back to in-memory lock.")

        # In-Memory Thread-Safe Fallback
        with self._lock:
            now = time.time()
            if idempotency_key in self._memory_idempotency:
                entry = self._memory_idempotency[idempotency_key]
                if now < entry["expires_at"]:
                    if payload and payload != "":
                        entry["payload"] = payload
                        return True, None
                    if entry["payload"] and entry["payload"] != "":
                        return False, entry["payload"]
                    return False, None
                else:
                    del self._memory_idempotency[idempotency_key]

            self._memory_idempotency[idempotency_key] = {
                "payload": payload or "",
                "expires_at": now + ttl_seconds,
            }
            return True, None

    def check_and_record_spend(
        self,
        merchant_id: str,
        user_id: str,
        amount: float,
        user_budget: float,
        merchant_cap: float,
    ) -> Tuple[bool, str, float, float]:
        """Atomically validates and updates spend limits using sub-ms Lua execution."""
        date_str = time.strftime("%Y-%m-%d")
        merchant_key = f"spend:merchant:{merchant_id}:{date_str}"
        user_key = f"spend:user:{user_id}:{date_str}"

        if self.redis_client:
            try:
                res = self.redis_client.eval(
                    LUA_SPEND_CAP_CHECK,
                    2,
                    merchant_key,
                    user_key,
                    str(amount),
                    str(user_budget),
                    str(merchant_cap),
                )
                approved = bool(res[0] == 1)
                reason = str(res[1])
                user_spend = float(res[2])
                merchant_spend = float(res[3])
                return approved, reason, user_spend, merchant_spend
            except Exception as e:
                logger.warning(f"Redis spend cap check error ({e}), falling back to in-memory check.")

        # In-Memory Thread-Safe Fallback
        with self._lock:
            current_user = self._memory_spend_user.get(user_key, 0.0)
            current_merch = self._memory_spend_merchant.get(merchant_key, 0.0)

            if amount > user_budget:
                return False, "EXCEEDS_SINGLE_TX_USER_BUDGET", current_user, current_merch

            if current_merch + amount > merchant_cap:
                return False, "EXCEEDS_MERCHANT_DAILY_CAP", current_user, current_merch

            self._memory_spend_user[user_key] = current_user + amount
            self._memory_spend_merchant[merchant_key] = current_merch + amount
            return (
                True,
                "APPROVED",
                self._memory_spend_user[user_key],
                self._memory_spend_merchant[merchant_key],
            )

    def release_spend(self, merchant_id: str, user_id: str, amount: float) -> None:
        """Rollback spend allocation on failure."""
        date_str = time.strftime("%Y-%m-%d")
        merchant_key = f"spend:merchant:{merchant_id}:{date_str}"
        user_key = f"spend:user:{user_id}:{date_str}"

        if self.redis_client:
            try:
                self.redis_client.incrbyfloat(merchant_key, -amount)
                self.redis_client.incrbyfloat(user_key, -amount)
                return
            except Exception as e:
                logger.warning(f"Redis release spend error: {e}")

        with self._lock:
            if merchant_key in self._memory_spend_merchant:
                self._memory_spend_merchant[merchant_key] = max(
                    0.0, self._memory_spend_merchant[merchant_key] - amount
                )
            if user_key in self._memory_spend_user:
                self._memory_spend_user[user_key] = max(
                    0.0, self._memory_spend_user[user_key] - amount
                )
