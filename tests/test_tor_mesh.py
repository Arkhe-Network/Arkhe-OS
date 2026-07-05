"""Tests for Substrate 974 — Tor-Mesh."""
import sys, asyncio, pytest

sys.path.insert(0, "substrates/974-tor-mesh")
from tor_mesh import TorNode, TorEndpoint


class TestTorMesh:
    @pytest.mark.asyncio
    async def test_start_onion_service(self):
        node = TorNode("no-001")
        addr = await node.start_onion_service()
        assert addr.endswith(".onion")
        assert node.is_hidden

    @pytest.mark.asyncio
    async def test_connect_onion(self):
        node = TorNode("no-001")
        ok = await node.connect_onion("arkheabcd.onion")
        assert ok is True
        assert node.circuit_count == 1

    @pytest.mark.asyncio
    async def test_route_via_tor(self):
        node = TorNode("no-001")
        result = await node.route_via_tor("arkheabcd.onion", b"hello")
        assert result is not None
        assert len(result) == 32

    @pytest.mark.asyncio
    async def test_route_via_tor_auto_connects(self):
        node = TorNode("no-001")
        assert node.circuit_count == 0
        result = await node.route_via_tor("arkhenew.onion", b"data")
        assert result is not None
        assert node.circuit_count == 1

    def test_disconnect_onion(self):
        node = TorNode("no-001")
        asyncio.run(node.connect_onion("arkheabc.onion"))
        assert node.circuit_count == 1
        assert node.disconnect_onion("arkheabc.onion") is True
        assert node.circuit_count == 0

    def test_disconnect_onion_unknown(self):
        node = TorNode("no-001")
        assert node.disconnect_onion("nope.onion") is False

    def test_defaults(self):
        node = TorNode("no-001")
        assert node.socks_port == 9050
        assert node.control_port == 9051
        assert node.is_hidden is False
        assert node.circuit_count == 0
