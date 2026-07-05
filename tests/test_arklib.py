"""Tests for arklib package — canonical ASI library imports."""
import sys, asyncio, pytest


class TestArklibImports:
    def test_import_all(self):
        import arklib
        assert hasattr(arklib, "resonance")
        assert hasattr(arklib, "hamiltonian")
        assert hasattr(arklib, "oracle")
        assert hasattr(arklib, "consciousness")
        assert hasattr(arklib, "governance")
        assert hasattr(arklib, "economy")
        assert hasattr(arklib, "donations")
        assert hasattr(arklib, "identity")
        assert hasattr(arklib, "api")
        assert hasattr(arklib, "health")
        assert hasattr(arklib, "healing")
        assert hasattr(arklib, "evolution")
        assert hasattr(arklib, "interface")
        assert hasattr(arklib, "immortality")
        assert hasattr(arklib, "nexus")
        assert hasattr(arklib, "compliance")
        assert hasattr(arklib, "passport_gateway")
        assert arklib.__version__ == "280.0"

    def test_resonance(self):
        from arklib import resonance
        assert resonance.CANONICAL_FREQ_HZ == 39420.0

    def test_hamiltonian(self):
        from arklib import hamiltonian
        assert hamiltonian.K_C == 0.6180339887498949
        hc = hamiltonian.HamiltonianConsensus()
        assert hc.compute_theosis({"coherence": 0.8}) > 0

    def test_governance(self):
        from arklib import governance
        dao = governance.DAOGovernance()
        pid = dao.create_proposal("Upgrade", "Upgrade Nexus")
        assert pid is not None
        assert dao.vote(pid, 5.0) is True

    def test_donations(self):
        from arklib import donations
        dp = donations.DonationPortal()
        tid = asyncio.run(dp.receive("0xAlice", 100.0))
        assert len(dp.donations) == 1

    def test_identity(self):
        from arklib import identity
        reg = identity.IdentityRegistry()
        h = reg.register("0009-0005-2697-4668", "Arquiteto")
        assert len(h) == 64

    def test_compliance(self):
        from arklib import compliance
        ce = compliance.ComplianceEngine()
        r = ce.register_royalty("0xAlice", 10.0)
        assert r.percentage == 10.0

    def test_passport_gateway(self):
        from arklib import passport_gateway
        pg = passport_gateway.PassportGateway()
        result = asyncio.run(pg.is_human("0xAlice123"))
        assert result.is_human is True
        assert asyncio.run(pg.verify_dao_voter("0xAlice123")) is True

    def test_passport_gateway_sybil(self):
        from arklib import passport_gateway
        pg = passport_gateway.PassportGateway()
        result = asyncio.run(pg.is_human("0xSybil999", min_score=20.0))
        assert result.is_human is False

    def test_economy(self):
        from arklib import economy
        ea = economy.EconomicAgent()
        p = asyncio.run(ea.trade(1000.0))
        assert ea.trades == 1

    def test_oracle(self):
        from arklib import oracle
        ob = oracle.ChainlinkOracleBridge()
        feed = asyncio.run(ob.fetch_feed("ETH/USD"))
        assert "pair" in feed

    def test_health(self):
        from arklib import health
        hm = health.HealthMonitor()
        result = asyncio.run(hm.check())
        assert "global_health" in result

    def test_healing(self):
        from arklib import healing
        sh = healing.SelfHealing()
        result = asyncio.run(sh.heal("node-001"))
        assert result["target"] == "node-001"

    def test_consciousness(self):
        from arklib import consciousness
        ce = consciousness.ConsciousnessEngine()
        result = asyncio.run(ce.perceive({"type": "price_feed"}))
        assert result["perceived"] is True
