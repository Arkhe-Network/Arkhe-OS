"""Tests for Substrate 975 — IPFS-Core."""
import sys, asyncio, pytest

sys.path.insert(0, "substrates/975-ipfs-core")
from ipfs_core import IPFSBackbone, ArkheArtifact


class TestIPFSBackbone:
    @pytest.mark.asyncio
    async def test_pin_returns_artifact(self):
        bb = IPFSBackbone()
        art = await bb.pin("decree-001", 973, "ARKHE-SEAL v1")
        assert isinstance(art, ArkheArtifact)
        assert art.name == "decree-001"
        assert art.substrate_id == 973
        assert art.cid is not None
        assert len(art.cid) == 64

    @pytest.mark.asyncio
    async def test_pin_adds_to_store(self):
        bb = IPFSBackbone()
        art = await bb.pin("decree-001", 973, "ARKHE-SEAL v1")
        assert bb.total_pins == 1
        got = await bb.get(art.cid)
        assert got is not None
        assert got.cid == art.cid

    @pytest.mark.asyncio
    async def test_pin_multiple(self):
        bb = IPFSBackbone()
        await bb.pin("a", 973, "data1")
        await bb.pin("b", 974, "data2")
        await bb.pin("c", 975, "data3")
        assert bb.total_pins == 3

    @pytest.mark.asyncio
    async def test_get_unknown(self):
        bb = IPFSBackbone()
        assert await bb.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_unpin(self):
        bb = IPFSBackbone()
        art = await bb.pin("test", 973, "data")
        assert bb.total_pins == 1
        ok = await bb.unpin(art.cid)
        assert ok is True
        assert bb.total_pins == 0

    @pytest.mark.asyncio
    async def test_unpin_unknown(self):
        bb = IPFSBackbone()
        ok = await bb.unpin("nope")
        assert ok is False

    @pytest.mark.asyncio
    async def test_connect_peer(self):
        bb = IPFSBackbone()
        ok = await bb.connect_peer("peer-12D3KooW")
        assert ok is True
        assert bb.total_peers == 1

    @pytest.mark.asyncio
    async def test_disconnect_peer(self):
        bb = IPFSBackbone()
        await bb.connect_peer("peer-abc")
        ok = await bb.disconnect_peer("peer-abc")
        assert ok is True
        assert bb.total_peers == 0

    @pytest.mark.asyncio
    async def test_disconnect_peer_unknown(self):
        bb = IPFSBackbone()
        ok = await bb.disconnect_peer("unknown")
        assert ok is False

    @pytest.mark.asyncio
    async def test_sync_with(self):
        bb = IPFSBackbone()
        await bb.pin("x", 973, "data")
        artifacts = await bb.sync_with("peer-abc")
        assert len(artifacts) == 1

    @pytest.mark.asyncio
    async def test_total_size_bytes(self):
        bb = IPFSBackbone()
        await bb.pin("a", 973, "1234567890")
        await bb.pin("b", 974, "abcdefghijklmnop")
        assert bb.total_size_bytes > 0
