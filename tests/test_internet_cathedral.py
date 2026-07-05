"""Tests for Substrate 972 — Internet-Cathedral."""
import sys, pytest
sys.path.insert(0, "substrates/972-internet-cathedral")
from internet_cathedral import InternetCathedralDeployer, DeployResult


class TestInternetCathedral:
    @pytest.mark.asyncio
    async def test_discover_targets(self):
        d = InternetCathedralDeployer()
        targets = await d.discover_targets()
        assert len(targets) == 4

    @pytest.mark.asyncio
    async def test_handshake_consent(self):
        d = InternetCathedralDeployer()
        assert await d.handshake({"ip": "1.1.1.1", "consent": True})

    @pytest.mark.asyncio
    async def test_handshake_no_consent(self):
        d = InternetCathedralDeployer()
        assert not await d.handshake({"ip": "1.1.1.1", "consent": False})

    @pytest.mark.asyncio
    async def test_inoculate_returns_id(self):
        d = InternetCathedralDeployer()
        nid = await d.inoculate({"ip": "1.1.1.1", "arch": "x86_64"})
        assert nid.startswith("node-")
        assert nid in d.deployed_nodes

    @pytest.mark.asyncio
    async def test_propagate(self):
        d = InternetCathedralDeployer()
        r = await d.propagate()
        assert len(r.deployed) == 3
        assert len(r.rejected) == 1

    @pytest.mark.asyncio
    async def test_propagate_rejected_is_non_consenting(self):
        d = InternetCathedralDeployer()
        r = await d.propagate()
        assert "198.51.100.22" in r.rejected
