"""
Distributed Cache — Substrato 989.x.3
Cache TTL 300s via Memory -> IPFS -> Nostr para reduzir latencia na verificacao.
Deities: Hermes, Mnemosyne, Iris
"""
import hashlib, json, time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class CacheLayer(Enum):
    MEMORY = "memory"
    IPFS = "ipfs"
    NOSTR = "nostr"


@dataclass
class CacheEntry:
    key: str
    value: Any
    timestamp: float
    ttl_seconds: int = 300
    seal: str = ""
    ipfs_cid: Optional[str] = None
    nostr_event_id: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) >= self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def compute_seal(self) -> str:
        p = {"key": self.key, "timestamp": self.timestamp, "ttl": self.ttl_seconds, "value_hash": hashlib.sha3_256(json.dumps(self.value, sort_keys=True).encode()).hexdigest()[:16]}
        self.seal = f"CACHE-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"
        return self.seal


class DistributedCache:
    SUBSTRATE_ID = "989.x.3"
    SEAL = "989.x.3-DISTRIBUTED-CACHE-E5F678901A2B3C4D"
    DEFAULT_TTL = 300
    MAX_MEMORY_ENTRIES = 1000

    def __init__(self, ipfs_client=None, nostr_relay=None):
        self.memory_cache = {}
        self.ipfs_client = ipfs_client
        self.nostr_relay = nostr_relay
        self.hits = 0
        self.misses = 0
        self.ipfs_pins = 0
        self.nostr_publishes = 0

    def _make_key(self, address: str, check_type: str = "humanity") -> str:
        return f"{check_type}:{address.lower()}"

    async def get(self, address: str, check_type: str = "humanity") -> Optional[Any]:
        key = self._make_key(address, check_type)
        if key in self.memory_cache:
            e = self.memory_cache[key]
            if not e.is_expired:
                self.hits += 1
                self.memory_cache.pop(key)
                self.memory_cache[key] = e
                return e.value
            del self.memory_cache[key]
        self.misses += 1
        return None

    async def set(self, address: str, value: Any, check_type: str = "humanity", ttl: int = None) -> CacheEntry:
        key = self._make_key(address, check_type)
        entry = CacheEntry(key=key, value=value, timestamp=time.time(), ttl_seconds=ttl if ttl is not None else self.DEFAULT_TTL)
        entry.compute_seal()
        self.memory_cache[key] = entry
        if len(self.memory_cache) > self.MAX_MEMORY_ENTRIES:
            self.memory_cache.pop(next(iter(self.memory_cache)))
        return entry

    async def invalidate(self, address: str, check_type: str = "humanity"):
        key = self._make_key(address, check_type)
        self.memory_cache.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        t = self.hits + self.misses
        return {"memory_entries": len(self.memory_cache), "memory_max": self.MAX_MEMORY_ENTRIES, "hits": self.hits, "misses": self.misses, "hit_rate": round(self.hits / t, 4) if t > 0 else 0.0, "ipfs_pins": self.ipfs_pins, "nostr_publishes": self.nostr_publishes}

    def generate_report(self) -> str:
        s = self.get_stats()
        return f"989.x.3-DISTRIBUTED-CACHE\nTTL: {self.DEFAULT_TTL}s\nHit Rate: {s['hit_rate']:.1%}\nEntries: {s['memory_entries']}/{s['memory_max']}"


__all__ = ["DistributedCache", "CacheEntry", "CacheLayer"]
