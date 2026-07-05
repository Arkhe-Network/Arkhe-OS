"""Tests for Substrate 972.1 — Nostr-Tor-IPFS-Bridge."""
import sys, asyncio, pytest

sys.path.insert(0, "substrates/9721-nostr-tor-ipfs-bridge")
from bridge import NostrBridge, TorBridge, IpfsBridge, NostrTorIpfsBridge, BridgeManifest


class TestNostrBridge:
    @pytest.mark.asyncio
    async def test_publish_event(self):
        nb = NostrBridge()
        eid = await nb.publish_event(30078, "ARKHE-SEAL v2")
        assert len(eid) == 64
        assert nb.total_sent == 1
        assert eid in nb.seen_events

    def test_is_connected(self):
        nb = NostrBridge()
        assert nb.is_connected is True


class TestTorBridge:
    @pytest.mark.asyncio
    async def test_create_circuit(self):
        tb = TorBridge()
        cid = await tb.create_circuit("arkhe123.onion")
        assert len(cid) == 12
        assert tb.active_circuits == 1

    @pytest.mark.asyncio
    async def test_send_via_onion(self):
        tb = TorBridge()
        ok, receipt = await tb.send_via_onion("arkhe456.onion", b"hello")
        assert ok is True
        assert len(receipt) == 64

    @pytest.mark.asyncio
    async def test_send_via_onion_auto_creates_circuit(self):
        tb = TorBridge()
        assert tb.active_circuits == 0
        ok, _ = await tb.send_via_onion("arkhenew.onion", b"data")
        assert ok is True
        assert tb.active_circuits == 1

    def test_empty_circuits(self):
        tb = TorBridge()
        assert tb.active_circuits == 0


class TestIpfsBridge:
    @pytest.mark.asyncio
    async def test_add_and_cat(self):
        ipfs = IpfsBridge()
        cid = await ipfs.add("ARKHE-SEAL v3")
        data = await ipfs.cat(cid)
        assert data == "ARKHE-SEAL v3"

    @pytest.mark.asyncio
    async def test_cat_unknown(self):
        ipfs = IpfsBridge()
        assert await ipfs.cat("nonexistent") is None

    @pytest.mark.asyncio
    async def test_pin(self):
        ipfs = IpfsBridge()
        cid = await ipfs.add("seal data")
        assert await ipfs.pin(cid) is True
        assert await ipfs.pin("unknown") is False

    def test_total_pinned(self):
        ipfs = IpfsBridge()
        assert ipfs.total_pinned == 0
        asyncio.run(ipfs.add("a"))
        assert ipfs.total_pinned == 1


class TestNostrTorIpfsBridge:
    @pytest.mark.asyncio
    async def test_nostr_to_ipfs(self):
        bridge = NostrTorIpfsBridge()
        manifest = await bridge.nostr_to_ipfs(30078, "ARKHE-SEAL v4")
        assert isinstance(manifest, BridgeManifest)
        assert manifest.source_channel == "nostr"
        assert manifest.target_channel == "ipfs"
        assert len(manifest.payload_hash) == 64

    @pytest.mark.asyncio
    async def test_tor_to_nostr(self):
        bridge = NostrTorIpfsBridge()
        manifest = await bridge.tor_to_nostr("arkhe789.onion")
        assert manifest.source_channel == "tor"
        assert manifest.target_channel == "nostr"
        assert manifest.payload_type == "circuit"

    @pytest.mark.asyncio
    async def test_ipfs_to_tor(self):
        bridge = NostrTorIpfsBridge()
        cid = await bridge.ipfs.add("secret data")
        manifest = await bridge.ipfs_to_tor(cid, "arkhe999.onion")
        assert manifest.source_channel == "ipfs"
        assert manifest.target_channel == "tor"
        assert len(manifest.payload_hash) == 64

    @pytest.mark.asyncio
    async def test_ipfs_to_tor_missing_cid(self):
        bridge = NostrTorIpfsBridge()
        with pytest.raises(ValueError, match="not found in IPFS"):
            await bridge.ipfs_to_tor("nonexistent", "arkhe.onion")

    @pytest.mark.asyncio
    async def test_bootstrap(self):
        bridge = NostrTorIpfsBridge()
        status = await bridge.bootstrap()
        assert status["nostr"]["connected"] is True
        assert status["tor"]["circuits"] == 0
        assert status["ipfs"]["pinned"] == 0

    @pytest.mark.asyncio
    async def test_manifest_log_accumulates(self):
        bridge = NostrTorIpfsBridge()
        await bridge.nostr_to_ipfs(30078, "msg1")
        await bridge.tor_to_nostr("arkhe111.onion")
        assert len(bridge.manifest_log) == 2
