"""Tests for Substrate 973 — Nostr-Relay."""
import sys, json, hashlib, asyncio, pytest

sys.path.insert(0, "substrates/973-nostr-relay")
from nostr_relay import CathedralNostrRelay, NostrEvent


def _make_event(pubkey="abc123", kind=30078, content="ARKHE-SEAL", tags=None) -> NostrEvent:
    if tags is None:
        tags = []
    created_at = 1700000000
    payload = json.dumps([0, pubkey, created_at, kind, tags, content])
    eid = hashlib.sha256(payload.encode()).hexdigest()
    return NostrEvent(id=eid, pubkey=pubkey, created_at=created_at, kind=kind, tags=tags, content=content, sig="deadbeef")


class TestNostrRelay:
    def test_handle_valid_event(self):
        relay = CathedralNostrRelay()
        ev = _make_event()
        result = asyncio.run(relay.handle_event(ev))
        assert result is True
        assert relay.total_received == 1
        assert relay.total_rejected == 0

    def test_handle_invalid_event(self):
        relay = CathedralNostrRelay()
        ev = _make_event()
        ev.id = "0000"  # tamper with id
        result = asyncio.run(relay.handle_event(ev))
        assert result is False
        assert relay.total_received == 1
        assert relay.total_rejected == 1

    def test_get_event_returns_event(self):
        relay = CathedralNostrRelay()
        ev = _make_event()
        asyncio.run(relay.handle_event(ev))
        got = relay.get_event(ev.id)
        assert got is not None
        assert got.content == "ARKHE-SEAL"

    def test_get_event_unknown(self):
        relay = CathedralNostrRelay()
        assert relay.get_event("nonexistent") is None

    def test_count_by_kind(self):
        relay = CathedralNostrRelay()
        asyncio.run(relay.handle_event(_make_event(kind=30078)))
        asyncio.run(relay.handle_event(_make_event(kind=30078, pubkey="def456")))
        asyncio.run(relay.handle_event(_make_event(kind=30079, content="ALERT")))
        assert relay.count_by_kind(30078) == 2
        assert relay.count_by_kind(30079) == 1
        assert relay.count_by_kind(99999) == 0

    def test_acceptance_rate(self):
        relay = CathedralNostrRelay()
        assert relay.acceptance_rate == 1.0
        asyncio.run(relay.handle_event(_make_event()))
        assert relay.acceptance_rate == 1.0
        ev = _make_event()
        ev.id = "bad"
        asyncio.run(relay.handle_event(ev))
        assert relay.acceptance_rate == 0.5

    def test_acceptance_rate_empty(self):
        relay = CathedralNostrRelay()
        assert relay.acceptance_rate == 1.0
