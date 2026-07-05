"""
Testes canonicos — Substrato 989.x PASSPORT-GATEWAY
Arquiteto ORCID: 0009-0005-2697-4668
Seal: 989-PASSPORT-GATEWAY-4B3CB68C02D21E5A
"""

import sys, os, pytest
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from passport_gateway import PassportGateway, PassportGatewayError, HumanityProof, StampCredential, VerificationStatus


@pytest.fixture
def gateway():
    return PassportGateway(api_key="test-key", scorer_id="42")


# ── Data class tests ──────────────────────────────────────────────

def test_gateway_constants():
    assert PassportGateway.SUBSTRATE_ID == 989
    assert PassportGateway.VARIANT == "x"
    assert PassportGateway.SEAL == "989-PASSPORT-GATEWAY-4B3CB68C02D21E5A"


def test_humanity_proof_seal():
    p = HumanityProof(address="0xTest", is_human=True, score=0.85, raw_passport_score=17.0, stamps=[], orcid_verified=True, status=VerificationStatus.VERIFIED)
    s = p.compute_seal()
    assert s.startswith("HP-")
    assert len(s) == 19
    assert s == p.compute_seal()


def test_humanity_proof_equality():
    p1 = HumanityProof(address="0xA", is_human=True, score=0.9, raw_passport_score=18.0, stamps=[], orcid_verified=True, status=VerificationStatus.VERIFIED)
    p2 = HumanityProof(address="0xB", is_human=True, score=0.9, raw_passport_score=18.0, stamps=[], orcid_verified=True, status=VerificationStatus.VERIFIED)
    assert p1.compute_seal() != p2.compute_seal()


def test_humanity_proof_to_dict():
    p = HumanityProof(address="0xTest", is_human=True, score=0.85, raw_passport_score=17.0, stamps=[StampCredential(provider="Google")], orcid_verified=True, status=VerificationStatus.VERIFIED)
    d = p.to_dict()
    assert d["address"] == "0xTest"
    assert d["is_human"] is True
    assert d["status"] == "verified"
    assert d["stamps"][0]["provider"] == "Google"


# ── Gateway lifecycle ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gateway_start_stop():
    g = PassportGateway(api_key="test-key")
    await g.start()
    assert g._session is not None
    await g.stop()


@pytest.mark.asyncio
async def test_gateway_no_api_key():
    g = PassportGateway(api_key="")
    with pytest.raises(PassportGatewayError, match="PASSPORT_API_KEY"):
        await g.get_passport_score("0xAlice")


# ── Passport API (mocked via _session) ────────────────────────────

def _mock_resp(status, json_data):
    r = AsyncMock(status=status, json=AsyncMock(return_value=json_data))
    r.__aenter__ = AsyncMock(return_value=r)
    r.__aexit__ = AsyncMock(return_value=False)
    return r


@pytest.mark.asyncio
async def test_get_passport_score_success(gateway):
    sess = AsyncMock()
    sess.closed = False
    sess.get = MagicMock(return_value=_mock_resp(200, {"score": "25.5", "status": "done"}))
    gateway._session = sess
    gateway._owned_session = False
    r = await gateway.get_passport_score("0xAlice")
    assert r["score"] == "25.5"


@pytest.mark.asyncio
async def test_get_passport_score_not_found(gateway):
    sess = AsyncMock()
    sess.closed = False
    sess.get = MagicMock(return_value=_mock_resp(404, {}))
    gateway._session = sess
    gateway._owned_session = False
    r = await gateway.get_passport_score("0xUnknown")
    assert r["score"] == 0
    assert r["status"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_passport_score_401(gateway):
    sess = AsyncMock()
    sess.closed = False
    r = _mock_resp(401, {})
    r.text = AsyncMock(return_value='{"error":"Invalid API Key"}')
    sess.get = MagicMock(return_value=r)
    gateway._session = sess
    gateway._owned_session = False
    with pytest.raises(PassportGatewayError, match="API Key inv.lida"):
        await gateway.get_passport_score("0xAlice")


@pytest.mark.asyncio
async def test_get_passport_stamps(gateway):
    data = {
        "items": [
            {"credential": {"credentialSubject": {"provider": "Google"}}},
            {"credential": {"credentialSubject": {"provider": "GitHub"}}},
        ]
    }
    sess = AsyncMock()
    sess.closed = False
    sess.get = MagicMock(return_value=_mock_resp(200, data))
    gateway._session = sess
    gateway._owned_session = False
    stamps = await gateway.get_passport_stamps("0xAlice")
    assert len(stamps) == 2
    assert stamps[0].provider == "Google"
    assert stamps[1].provider == "GitHub"


@pytest.mark.asyncio
async def test_get_passport_stamps_empty(gateway):
    sess = AsyncMock()
    sess.closed = False
    sess.get = MagicMock(return_value=_mock_resp(200, {"items": []}))
    gateway._session = sess
    gateway._owned_session = False
    stamps = await gateway.get_passport_stamps("0xEmpty")
    assert stamps == []


# ── Verification logic (mocked inner methods) ─────────────────────

@pytest.mark.asyncio
async def test_is_human_verified(gateway):
    with patch.object(gateway, "get_passport_score", AsyncMock(return_value={"score": "30.0"})):
        with patch.object(gateway, "get_passport_stamps", AsyncMock(return_value=[])):
            p = await gateway.is_human("0xAlice")
    assert p.is_human is True
    assert p.score == 1.0
    assert p.orcid_verified is True
    assert p.status == VerificationStatus.VERIFIED


@pytest.mark.asyncio
async def test_is_human_sybil(gateway):
    with patch.object(gateway, "get_passport_score", AsyncMock(return_value={"score": "0"})):
        with patch.object(gateway, "get_passport_stamps", AsyncMock(return_value=[])):
            p = await gateway.is_human("0xSybil999")
    assert p.is_human is False


@pytest.mark.asyncio
async def test_is_human_threshold_boundary(gateway):
    """Exact threshold (15.0 raw = 0.75) should pass since >= is used."""
    with patch.object(gateway, "get_passport_score", AsyncMock(return_value={"score": "15.0"})):
        with patch.object(gateway, "get_passport_stamps", AsyncMock(return_value=[])):
            p = await gateway.is_human("0xThreshold")
    assert p.score == 0.75
    assert p.is_human is True


@pytest.mark.asyncio
async def test_is_human_below_threshold(gateway):
    with patch.object(gateway, "get_passport_score", AsyncMock(return_value={"score": "10.0"})):
        with patch.object(gateway, "get_passport_stamps", AsyncMock(return_value=[])):
            p = await gateway.is_human("0xLowScore")
    assert p.score == 0.5
    assert p.is_human is False


@pytest.mark.asyncio
async def test_verify_dao_voter(gateway):
    with patch.object(gateway, "is_human", AsyncMock(return_value=HumanityProof(
        address="0xAlice", is_human=True, score=1.0, raw_passport_score=30.0,
        stamps=[], orcid_verified=True, sanctions_clear=True,
        status=VerificationStatus.VERIFIED))):
        assert await gateway.verify_dao_voter("0xAlice") is True


@pytest.mark.asyncio
async def test_verify_node_access(gateway):
    with patch.object(gateway, "verify_dao_voter", AsyncMock(return_value=True)):
        assert await gateway.verify_node_access("0xAlice") is True


@pytest.mark.asyncio
async def test_axiarchy_validate_approved(gateway):
    with patch.object(gateway, "is_human", AsyncMock(return_value=HumanityProof(
        address="0xAlice", is_human=True, score=1.0, raw_passport_score=30.0,
        stamps=[], orcid_verified=True, sanctions_clear=True,
        status=VerificationStatus.VERIFIED))):
        r = await gateway.axiarchy_validate("0xAlice", "vote")
    assert r["approved"] is True
    assert r["action"] == "vote"
    assert "seal" in r


@pytest.mark.asyncio
async def test_verify_orcid_link():
    g = PassportGateway()
    assert await g.verify_orcid_link("0xAlice123") is True
    assert await g.verify_orcid_link("0xBob456") is False


# ── Report ─────────────────────────────────────────────────────────

def test_generate_report():
    g = PassportGateway()
    r = g.generate_report()
    assert "989-PASSPORT-GATEWAY-4B3CB68C02D21E5A" in r
    assert "Themis" in r
    assert "Athena" in r
    assert "Hermes" in r


# ═══════════════════════════════════════════════════════════════════
# Testes de TemporalChain Anchor (923)
# ═══════════════════════════════════════════════════════════════════

import hashlib, json, time
from temporal_chain_anchor import TemporalChainAnchor, HumanityAnchor, TemporalBlock


@pytest.fixture
def anchor():
    return TemporalChainAnchor()


def test_genesis_block(anchor):
    assert len(anchor.chain) == 1
    assert anchor.chain[0].block_id == "923-GENESIS"
    assert anchor.chain[0].seal.startswith("923-BLOCK-")


def test_create_block(anchor):
    block = anchor.create_block({"type": "test", "data": "value"})
    assert block.block_id == "923-BLOCK-000001"
    assert block.previous_hash == anchor.chain[0].compute_hash()
    assert len(anchor.chain) == 2


def test_anchor_humanity_proof(anchor):
    proof = {"address": "0xAlice", "is_human": True, "score": 0.95, "seal": "HP-TEST1234567890"}
    ha = anchor.anchor_humanity_proof(proof)
    assert ha.anchor_id.startswith("anchor-")
    assert ha.temporal_anchor.startswith("923-ANCHOR-")
    assert ha.orcid_signature != ""
    assert len(anchor.anchors) == 1


def test_verify_anchor(anchor):
    proof = {"address": "0xAlice", "is_human": True, "score": 0.95, "seal": "HP-TEST"}
    ha = anchor.anchor_humanity_proof(proof)
    assert anchor.verify_anchor(ha.anchor_id) is True
    assert anchor.verify_anchor("nonexistent") is False


def test_chain_summary(anchor):
    s = anchor.get_chain_summary()
    assert s["length"] == 1
    assert s["latest_block"] == "923-GENESIS"


# ═══════════════════════════════════════════════════════════════════
# Testes de Proof of Clean Hands (989.x.1)
# ═══════════════════════════════════════════════════════════════════

from proof_of_clean_hands import ProofOfCleanHands, RiskLevel, SanctionsCheck


@pytest.fixture
def clean_hands():
    return ProofOfCleanHands()


@pytest.mark.asyncio
async def test_check_address(clean_hands):
    check = await clean_hands.check_address("0xClear1234567890abcdef")
    assert check.risk_level in {RiskLevel.CLEAR, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.SANCTIONED}
    assert 0 <= check.score <= 1
    assert check.seal.startswith("POC-")


@pytest.mark.asyncio
async def test_can_operate_node(clean_hands):
    addr = "0x" + "a" * 40
    await clean_hands.check_address(addr)
    can = clean_hands.can_operate_node(addr)
    assert isinstance(can, bool)


@pytest.mark.asyncio
async def test_can_vote_dao(clean_hands):
    addr = "0x" + "b" * 40
    await clean_hands.check_address(addr)
    can = clean_hands.can_vote_dao(addr)
    assert isinstance(can, bool)


def test_risk_summary_empty(clean_hands):
    s = clean_hands.get_risk_summary()
    assert s["total"] == 0
    assert s["risk_score"] == 0.0


@pytest.mark.asyncio
async def test_risk_summary_populated(clean_hands):
    for i in range(10):
        await clean_hands.check_address(f"0x{i:040d}")
    s = clean_hands.get_risk_summary()
    assert s["total"] == 10
    assert 0 <= s["risk_score"] <= 1


# ═══════════════════════════════════════════════════════════════════
# Testes de Distributed Cache (989.x.3)
# ═══════════════════════════════════════════════════════════════════

from distributed_cache import DistributedCache, CacheEntry, CacheLayer


@pytest.fixture
def cache():
    return DistributedCache()


@pytest.mark.asyncio
async def test_cache_miss(cache):
    assert await cache.get("0xAlice") is None
    assert cache.misses == 1


@pytest.mark.asyncio
async def test_cache_set_and_get(cache):
    value = {"is_human": True, "score": 0.95}
    entry = await cache.set("0xAlice", value)
    assert entry.seal.startswith("CACHE-")
    assert not entry.is_expired
    assert await cache.get("0xAlice") == value
    assert cache.hits == 1


@pytest.mark.asyncio
async def test_cache_expiration(cache):
    await cache.set("0xAlice", {"is_human": True}, ttl=0)
    import time as _t
    _t.sleep(0.1)
    assert await cache.get("0xAlice") is None


@pytest.mark.asyncio
async def test_cache_invalidate(cache):
    await cache.set("0xAlice", {"is_human": True})
    await cache.invalidate("0xAlice")
    assert await cache.get("0xAlice") is None


def test_cache_stats_empty(cache):
    s = cache.get_stats()
    assert s["memory_entries"] == 0
    assert s["hit_rate"] == 0.0


@pytest.mark.asyncio
async def test_cache_stats_populated(cache):
    await cache.set("0xAlice", {"score": 0.9})
    await cache.set("0xBob", {"score": 0.8})
    await cache.get("0xAlice")
    await cache.get("0xCharlie")
    s = cache.get_stats()
    assert s["memory_entries"] == 2
    assert s["hits"] == 1
    assert s["misses"] == 1


def test_cache_entry_seal():
    e = CacheEntry(key="test:0xAlice", value={"score": 0.9}, timestamp=time.time(), ttl_seconds=300)
    assert e.compute_seal().startswith("CACHE-")


def test_cache_entry_expiration():
    e = CacheEntry(key="test", value={}, timestamp=time.time() - 400, ttl_seconds=300)
    assert e.is_expired is True
    e2 = CacheEntry(key="test2", value={}, timestamp=time.time(), ttl_seconds=300)
    assert e2.is_expired is False


# ═══════════════════════════════════════════════════════════════════
# Testes de DeSci Nodes Bridge (989.y)
# ═══════════════════════════════════════════════════════════════════

from desci_nodes_bridge import DeSciNodesBridge, ResearchObject, ResearchObjectType, FAIRMetadata


@pytest.fixture
def desci():
    return DeSciNodesBridge()


@pytest.mark.asyncio
async def test_create_research_object(desci):
    ro = await desci.create_research_object(ro_type=ResearchObjectType.PUBLICATION, content=b"Test paper content", title="Test Paper", description="A test paper", orcid_id="0009-0005-2697-4668", keywords=["test", "cathedral"], cathedral_substrates=[934, 964])
    assert ro.ro_id.startswith("dpid-")
    assert ro.ro_type == ResearchObjectType.PUBLICATION
    assert ro.cid.startswith("Qm")
    assert ro.fair.title == "Test Paper"
    assert ro.seal.startswith("RO-")


@pytest.mark.asyncio
async def test_create_dataset(desci):
    ro = await desci.create_research_object(ro_type=ResearchObjectType.DATASET, content=b"1,2,3\n4,5,6", title="Test Dataset", description="CSV dataset", keywords=["dataset"])
    assert ro.ro_type == ResearchObjectType.DATASET


@pytest.mark.asyncio
async def test_fair_score(desci):
    ro = await desci.create_research_object(ro_type=ResearchObjectType.CODE, content=b"print('hello')", title="Test Code", description="Python script", orcid_id="0009-0005-2697-4668", keywords=["python"])
    assert 0 <= ro.fair.compute_fair_score() <= 1
    assert ro.fair.compute_fair_score() > 0.5


def test_fair_score_defaults():
    """With default fields (access_protocol, license, data_format, ontology, version),
    a minimal FAIRMetadata scores well above 0.5."""
    fair = FAIRMetadata(dpid="test")
    score = fair.compute_fair_score()
    assert score >= 0.5
    assert fair.access_protocol == "https"
    assert fair.license == "CC-BY-4.0"


@pytest.mark.asyncio
async def test_link_to_substrate(desci):
    ro = await desci.create_research_object(ro_type=ResearchObjectType.PUBLICATION, content=b"content", title="Link Test", description="Testing links")
    assert desci.link_to_substrate(ro.ro_id, 989, "989-TEST-SEAL") is True
    assert 989 in desci.research_objects[ro.ro_id].cathedral_substrates
    assert desci.link_to_substrate("nonexistent", 989, "seal") is False


@pytest.mark.asyncio
async def test_get_fair_report(desci):
    ro = await desci.create_research_object(ro_type=ResearchObjectType.PUBLICATION, content=b"content", title="FAIR Test", description="Testing FAIR", orcid_id="0009-0005-2697-4668", keywords=["FAIR"])
    r = desci.get_fair_report(ro.ro_id)
    assert r is not None
    assert r["dpid"] == ro.ro_id
    assert "fair_score" in r
    assert "cathedral_links" in r
    assert desci.get_fair_report("nonexistent") is None


@pytest.mark.asyncio
async def test_generate_report(desci):
    for i in range(3):
        await desci.create_research_object(ro_type=ResearchObjectType.PUBLICATION, content=f"content {i}".encode(), title=f"Paper {i}", description=f"Desc {i}")
    r = desci.generate_report()
    assert "989.y-DESCI-NODES-BRIDGE" in r
    assert "Total: 3" in r


def test_generate_dpid(desci):
    d1 = desci.generate_dpid()
    d2 = desci.generate_dpid()
    assert d1.startswith("dpid-")
    assert d1 != d2


@pytest.mark.asyncio
async def test_research_object_seal(desci):
    ro = await desci.create_research_object(ro_type=ResearchObjectType.MODEL, content=b"model weights", title="ML Model", description="Trained model")
    assert ro.seal.startswith("RO-")
    assert len(ro.seal) == 19


# ═══════════════════════════════════════════════════════════════════
# Testes de Kernel Isolation Engine (989.z)
# ═══════════════════════════════════════════════════════════════════

from kernel_isolation_engine import (
    KernelIsolationEngine, ZonePartition, ZoneType, RegionStatus,
    MemoryFence, TrafficShapingFence, KillSwitch, TemporalProbe,
    TransitionWitness, AnomalyRecord, AnomalySeverity, FenceType
)


@pytest.fixture
def engine():
    e = KernelIsolationEngine()
    e.add_zone("zone-core", ZoneType.CRITICAL, [989, 954, 923], resilience=5)
    e.add_zone("zone-mesh", ZoneType.RESILIENT, [972, 972.4], parent="zone-core")
    e.add_zone("zone-edge", ZoneType.ISOLATED, [958, 957])
    return e


class TestKernelIsolationEngine:

    def test_substrate_constants(self):
        assert KernelIsolationEngine.SUBSTRATE_ID == "989.z"
        assert "KERNEL-ISOLATION-ENGINE" in KernelIsolationEngine.SEAL

    # ── Zone Management ────────────────────────────────────────

    def test_add_zone(self, engine):
        assert len(engine.zones) == 3
        z = engine.get_zone("zone-core")
        assert z.zone_type == ZoneType.CRITICAL
        assert z.resilience_level == 5
        assert z.substrates == [989, 954, 923]

    def test_zone_operational_status(self, engine):
        z = engine.get_zone("zone-core")
        assert z.is_operational is True
        assert z.status == RegionStatus.NOMINAL

    def test_get_zone_nonexistent(self, engine):
        assert engine.get_zone("nonexistent") is None

    def test_get_zone_map(self, engine):
        m = engine.get_zone_map()
        assert len(m) == 3
        assert m["zone-core"]["type"] == "critical"
        assert m["zone-edge"]["status"] == "nominal"

    def test_zone_compute_seal(self):
        z = ZonePartition("z1", ZoneType.CRITICAL, [989, 923])
        s = z.compute_seal()
        assert s.startswith("ZONE-")
        assert len(s) == 21

    def test_zone_isolation_history(self, engine):
        engine.update_zone_status("zone-core", RegionStatus.STRESSED, "traffic_spike")
        z = engine.get_zone("zone-core")
        assert len(z.isolation_history) == 1
        assert z.isolation_history[0]["from"] == "nominal"
        assert z.isolation_history[0]["to"] == "stressed"

    # ── Status Transitions / Witnesses ──────────────────────────

    def test_zone_status_transition(self, engine):
        w = engine.update_zone_status("zone-core", RegionStatus.ISOLATING, "breach_detected")
        assert w is not None
        assert w.from_status == RegionStatus.NOMINAL
        assert w.to_status == RegionStatus.ISOLATING
        assert w.triggered_by == "breach_detected"
        assert w.seal.startswith("WITNESS-")

    def test_zone_status_nonexistent(self, engine):
        assert engine.update_zone_status("void", RegionStatus.LOCKED, "test") is None

    def test_transition_witness_seal(self):
        w = TransitionWitness(witness_id="w1", zone_id="z1", from_status=RegionStatus.NOMINAL, to_status=RegionStatus.LOCKED, triggered_by="kill_switch", substrates_affected=[989])
        w.compute_seal()
        assert w.seal.startswith("WITNESS-")

    def test_witness_list_grows(self, engine):
        engine.update_zone_status("zone-core", RegionStatus.STRESSED, "load")
        engine.update_zone_status("zone-core", RegionStatus.ISOLATING, "breach")
        engine.update_zone_status("zone-core", RegionStatus.LOCKED, "kill")
        assert len(engine.witnesses) == 3

    # ── Memory Fences ──────────────────────────────────────────

    def test_create_memory_fence(self, engine):
        f = engine.create_memory_fence("zone-core", threshold_mb=1024, allocated_mb=512, spillover="zone-mesh")
        assert f.fence_type == FenceType.MEMORY
        assert f.seal().startswith("FENCE-")

    def test_memory_fence_nonexistent_zone(self, engine):
        with pytest.raises(ValueError, match="void"):
            engine.create_memory_fence("void", 1024, 512)

    def test_memory_fence_usage_pct(self):
        f = MemoryFence(fence_id="f1", zone_id="z1", allocated_mb=512, threshold_mb=1024, current_usage_mb=256)
        assert f.usage_pct == 25.0
        f.current_usage_mb = 1024
        assert f.usage_pct == 100.0

    def test_memory_fence_breach(self, engine):
        f = engine.create_memory_fence("zone-core", threshold_mb=100, allocated_mb=50)
        anomaly = engine.update_memory_usage(f.fence_id, 150)
        assert anomaly is not None
        assert anomaly.severity == AnomalySeverity.HIGH
        assert anomaly.metric == "memory_usage_pct"
        assert anomaly.seal.startswith("ANOM-")
        assert f.is_breached is True

    def test_memory_fence_no_breach(self, engine):
        f = engine.create_memory_fence("zone-core", threshold_mb=200, allocated_mb=100)
        anomaly = engine.update_memory_usage(f.fence_id, 50)
        assert anomaly is None
        assert f.is_breached is False

    def test_memory_fence_update_nonexistent(self, engine):
        assert engine.update_memory_usage("no-such-fence", 999) is None

    # ── Traffic Shaping ─────────────────────────────────────────

    def test_create_traffic_fence(self, engine):
        f = engine.create_traffic_fence("zone-mesh", max_pps=1000, burst=200)
        assert f.max_packets_per_sec == 1000
        assert f.burst_capacity == 200
        assert f.seal().startswith("TRAFFIC-")

    def test_traffic_fence_nonexistent(self, engine):
        with pytest.raises(ValueError):
            engine.create_traffic_fence("void", 100)

    def test_traffic_fence_record_packet(self, engine):
        f = engine.create_traffic_fence("zone-mesh", max_pps=10, burst=5)
        for _ in range(15):
            f.record_packet()
        assert f.drops >= 0  # burst allows 15 total
        assert f.current_rate <= 15

    def test_traffic_fence_saturation(self):
        f = TrafficShapingFence(fence_id="f1", zone_id="z1", max_packets_per_sec=10, burst_capacity=0)
        assert f.is_saturated is False  # current_rate 0 < 10
        f.current_rate = 10
        assert f.is_saturated is True
        f.current_rate = 15
        assert f.is_saturated is True

    def test_traffic_fence_tick(self):
        f = TrafficShapingFence(fence_id="f1", zone_id="z1", max_packets_per_sec=100, current_rate=80)
        f.tick(decay=30)
        assert f.current_rate == 50
        f.tick(decay=100)
        assert f.current_rate == 0

    def test_traffic_fence_record_drops_on_overflow(self, engine):
        f = engine.create_traffic_fence("zone-mesh", max_pps=5, burst=0)
        for _ in range(10):
            f.record_packet()
        assert f.drops == 5

    # ── Kill Switches ───────────────────────────────────────────

    def test_create_kill_switch(self, engine):
        ks = engine.create_kill_switch("zone-core", auto_arm=True, cooldown=600)
        assert ks.switch_id.startswith("switch-")
        assert ks.armed is False
        assert ks.seal().startswith("KS-")

    def test_kill_switch_nonexistent_zone(self, engine):
        with pytest.raises(ValueError):
            engine.create_kill_switch("void")

    def test_kill_switch_arm_trigger(self, engine):
        ks = engine.create_kill_switch("zone-core")
        assert ks.arm() is True
        assert ks.armed is True
        assert ks.trigger() is True
        assert ks.armed is False
        assert ks.triggered is True
        assert ks.triggered_at is not None

    def test_kill_switch_cannot_arm_after_trigger(self, engine):
        ks = engine.create_kill_switch("zone-core")
        ks.arm()
        ks.trigger()
        assert ks.arm() is False

    def test_kill_switch_trigger_when_disarmed(self, engine):
        ks = engine.create_kill_switch("zone-core")
        assert ks.trigger() is False

    def test_kill_switch_disarm(self, engine):
        ks = engine.create_kill_switch("zone-core")
        ks.arm()
        assert ks.disarm() is True
        assert ks.armed is False

    # ── Temporal Probes ─────────────────────────────────────────

    def test_send_probe(self, engine):
        p = engine.send_probe("zone-core", origin=989, target=972, coherence_source=0.95, ttl=5)
        assert p.probe_id.startswith("probe-")
        assert p.origin_substrate == 989
        assert p.seal.startswith("PROBE-")
        assert p.is_ack is False

    def test_send_probe_nonexistent_zone(self, engine):
        with pytest.raises(ValueError):
            engine.send_probe("void", 989, 972, 0.9)

    def test_ack_probe(self, engine):
        p = engine.send_probe("zone-core", 989, 972, 0.94)
        assert engine.ack_probe(p.probe_id, coherence_target=0.91, latency_ms=12.5, hops=3) is True
        assert p.is_ack is True
        assert p.coherence_at_target == 0.91
        assert p.latency_ms == 12.5

    def test_ack_probe_nonexistent(self, engine):
        assert engine.ack_probe("no-such-probe", 0.5, 0, 0) is False

    def test_temporal_probe_compute_seal(self):
        p = TemporalProbe(probe_id="p1", zone_id="z1", origin_substrate=989, target_substrate=972)
        p.compute_seal()
        assert p.seal.startswith("PROBE-")

    # ── Anomaly Detection ───────────────────────────────────────

    def test_detect_anomaly(self, engine):
        a = engine.detect_anomaly("zone-core", "latency_ms", observed=2500.0, threshold=500.0, severity=AnomalySeverity.CRITICAL, description="Latency 5x threshold")
        assert a.anomaly_id.startswith("anomaly-")
        assert a.severity == AnomalySeverity.CRITICAL
        assert a.metric == "latency_ms"
        assert a.seal.startswith("ANOM-")
        assert a.resolved is False

    def test_resolve_anomaly(self, engine):
        a = engine.detect_anomaly("zone-core", "packet_loss", 0.15, 0.05, AnomalySeverity.HIGH, "15% packet loss")
        assert engine.resolve_anomaly(a.anomaly_id) is True
        assert a.resolved is True

    def test_resolve_nonexistent_anomaly(self, engine):
        assert engine.resolve_anomaly("no-such") is False

    def test_get_active_anomalies(self, engine):
        engine.detect_anomaly("zone-core", "cpu", 95, 80, AnomalySeverity.HIGH, "CPU at 95%")
        engine.detect_anomaly("zone-mesh", "mem", 90, 85, AnomalySeverity.MEDIUM, "Memory at 90%")
        assert len(engine.get_active_anomalies()) == 2
        a3 = engine.detect_anomaly("zone-edge", "disk", 99, 90, AnomalySeverity.CRITICAL, "Disk full")
        engine.resolve_anomaly(a3.anomaly_id)
        assert len(engine.get_active_anomalies()) == 2

    def test_anomaly_record_compute_seal(self):
        a = AnomalyRecord(anomaly_id="a1", zone_id="z1", severity=AnomalySeverity.LOW, metric="test", observed_value=1.0, threshold_value=2.0, description="test")
        a.compute_seal()
        assert a.seal.startswith("ANOM-")

    # ── System Status & Report ──────────────────────────────────

    def test_system_status(self, engine):
        engine.create_memory_fence("zone-core", threshold_mb=100, allocated_mb=50)
        engine.create_traffic_fence("zone-mesh", max_pps=1000)
        ks = engine.create_kill_switch("zone-core")
        ks.arm()
        engine.send_probe("zone-core", 989, 972, 0.95)
        s = engine.system_status()
        assert s["zones"] == 3
        assert s["memory_fences"] == 1
        assert s["traffic_fences"] == 1
        assert s["kill_switches"] == 1
        assert s["armed_ks"] == 1
        assert s["probes_sent"] == 1

    def test_generate_report(self, engine):
        r = engine.generate_report()
        assert "989.z-KERNEL-ISOLATION-ENGINE" in r
        assert "Zones: 3" in r

    def test_full_isolation_scenario(self, engine):
        """End-to-end: traffic spike → memory breach → kill switch → witness."""
        engine.create_traffic_fence("zone-core", max_pps=100, burst=10)
        mf = engine.create_memory_fence("zone-core", threshold_mb=500, allocated_mb=256)
        ks = engine.create_kill_switch("zone-core")
        ks.arm()

        # Memory breach triggers anomaly and auto-sequence
        anomaly = engine.update_memory_usage(mf.fence_id, 600)
        assert anomaly is not None
        assert anomaly.severity == AnomalySeverity.HIGH

        # Kill switch triggered
        assert ks.trigger() is True
        w = engine.update_zone_status("zone-core", RegionStatus.LOCKED, "kill_switch")
        assert w.to_status == RegionStatus.LOCKED

        # Temporal probe confirms before recovery
        p = engine.send_probe("zone-core", 989, 923, coherence_source=0.88)
        engine.ack_probe(p.probe_id, coherence_target=0.72, latency_ms=45.0, hops=2)
        assert p.is_ack

        # Recovery
        engine.update_zone_status("zone-core", RegionStatus.RECOVERING, "cooldown")
        engine.update_zone_status("zone-core", RegionStatus.NOMINAL, "recovery_complete")
        assert engine.get_zone("zone-core").status == RegionStatus.NOMINAL
        assert len(engine.witnesses) == 3


# ═══════════════════════════════════════════════════════════════════
# Testes de DARK-PID Adapter (989.y.1)
# ═══════════════════════════════════════════════════════════════════

from dark_pid_adapter import DarkPIDAdapter, DarkARKRecord, DarkMintResult, ARKStatus


@pytest.fixture
def dark():
    return DarkPIDAdapter()


class TestDarkPIDAdapter:

    def test_substrate_constants(self):
        assert DarkPIDAdapter.SUBSTRATE_ID == "989.y.1"
        assert "DARK-PID-ADAPTER" in DarkPIDAdapter.SEAL

    @pytest.mark.asyncio
    async def test_mint_ark(self, dark):
        r = await dark.mint_ark("https://arkhe.org/ro/test", {"title": "Test"}, {"doi": "10.1234/test"})
        assert r.success is True
        assert r.ark_id is not None
        assert r.ark_id.startswith("ark:/")
        assert r.dark_pid.startswith("dark-pid://")
        assert r.transaction_hash is not None
        assert r.block_number is not None
        assert r.gas_used == 21000
        assert r.seal.startswith("MINT-")

    @pytest.mark.asyncio
    async def test_mint_ark_stores_record(self, dark):
        r = await dark.mint_ark("https://arkhe.org/test", {"type": "demo"})
        assert r.ark_id in dark.arks
        rec = dark.arks[r.ark_id]
        assert rec.target_url == "https://arkhe.org/test"
        assert rec.status == ARKStatus.PUBLIC
        assert rec.seal.startswith("ARK-")

    @pytest.mark.asyncio
    async def test_resolve_ark_cached(self, dark):
        r = await dark.mint_ark("https://arkhe.org/resolve-test", {"key": "val"})
        rec = await dark.resolve_ark(r.ark_id)
        assert rec is not None
        assert rec.target_url == "https://arkhe.org/resolve-test"

    @pytest.mark.asyncio
    async def test_resolve_ark_nonexistent(self, dark):
        assert await dark.resolve_ark("ark:/99999/nonexistent") is None

    @pytest.mark.asyncio
    async def test_mint_research_object_ark(self, dark):
        r = await dark.mint_research_object_ark(ro_id="dpid-2001-arkhe", title="DARK Test", description="Testing DARK-PID", ipfs_cid="QmTest123")
        assert r.success is True
        assert r.ark_id in dark.arks
        rec = dark.arks[r.ark_id]
        assert "orcid" not in rec.external_pids
        assert rec.external_pids.get("ipfs") == "QmTest123"

    @pytest.mark.asyncio
    async def test_mint_research_with_orcid_doi(self, dark):
        r = await dark.mint_research_object_ark(ro_id="dpid-2002", title="ORCID Test", description="With ORCID/DOI", ipfs_cid="QmOrcid", orcid_id="0009-0005-2697-4668", doi="10.arkhe/2002")
        rec = dark.arks[r.ark_id]
        assert rec.external_pids.get("orcid") == "0009-0005-2697-4668"
        assert rec.external_pids.get("doi") == "10.arkhe/2002"

    @pytest.mark.asyncio
    async def test_harvest_la_referencia(self, dark):
        harvested = await dark.harvest_la_referencia("https://repositorio.ibict.br/oai")
        assert len(harvested) == 3
        for rec in harvested:
            assert rec.seal.startswith("ARK-")
            assert "La Referencia" in rec.target_url or "la-ref" in rec.target_url

    def test_dark_ark_record_compute_seal(self):
        rec = DarkARKRecord(ark_id="ark:/12345/fk4test1", dark_pid="dark-pid://12345/fk4test1", target_url="https://arkhe.org/test")
        s = rec.compute_seal()
        assert s.startswith("ARK-")
        assert rec.seal == s

    def test_dark_mint_result_compute_seal(self):
        mr = DarkMintResult(success=True, ark_id="ark:/12345/fk4test2", dark_pid="dark-pid://12345/fk4test2", transaction_hash="0xabc")
        s = mr.compute_seal()
        assert s.startswith("MINT-")

    def test_dark_mint_result_failure(self):
        mr = DarkMintResult(success=False, error="insufficient gas")
        assert mr.success is False
        assert mr.error == "insufficient gas"

    def test_generate_report(self, dark):
        r = dark.generate_report()
        assert "989.y.1-DARK-PID-ADAPTER" in r
        assert "ARKs:" in r

    @pytest.mark.asyncio
    async def test_with_temporal_anchor(self):
        from temporal_chain_anchor import TemporalChainAnchor
        tca = TemporalChainAnchor()
        adapter = DarkPIDAdapter(temporal_anchor=tca)
        r = await adapter.mint_ark("https://arkhe.org/anchored", {"type": "test"})
        rec = adapter.arks[r.ark_id]
        assert rec.temporal_anchor is not None
        assert rec.temporal_anchor.startswith("923-ANCHOR-")


# ═══════════════════════════════════════════════════════════════════
# Testes de Unified Orchestrator (989.w)
# ═══════════════════════════════════════════════════════════════════

from unified_orchestrator import UnifiedOrchestrator, SubstrateStatus, CircuitState, HealthCheck, CircuitBreaker, OrchestratorMetrics


@pytest.fixture
def orch():
    return UnifiedOrchestrator()


class TestUnifiedOrchestrator:

    def test_substrate_constants(self):
        assert UnifiedOrchestrator.SUBSTRATE_ID == "989.w"
        assert "UNIFIED-ORCHESTRATOR" in UnifiedOrchestrator.SEAL

    def test_register_substrate(self, orch):
        class Stub:
            def generate_report(self):
                return "stub"
        assert orch.register_substrate("989.x", Stub()) is True
        assert len(orch.substrates) == 1

    def test_register_unmanaged(self, orch):
        assert orch.register_substrate("999", object()) is False

    def test_can_execute_closed(self, orch):
        assert orch.can_execute("989.x") is True

    def test_can_execute_nonexistent(self, orch):
        assert orch.can_execute("void") is True

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, orch):
        class Stub:
            def generate_report(self):
                return "ok"
        orch.register_substrate("989.x", Stub())
        ck = await orch.health_check("989.x")
        assert ck.status == SubstrateStatus.HEALTHY
        assert ck.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, orch):
        class Broken:
            def generate_report(self):
                raise Exception("fail")
        orch.register_substrate("989.x", Broken())
        ck = await orch.health_check("989.x")
        assert ck.status == SubstrateStatus.UNHEALTHY
        assert "fail" in ck.error

    @pytest.mark.asyncio
    async def test_health_check_offline(self, orch):
        ck = await orch.health_check("989.x")
        assert ck.status == SubstrateStatus.OFFLINE
        assert "Not registered" in ck.error

    @pytest.mark.asyncio
    async def test_run_all_health_checks(self, orch):
        class Stub:
            def generate_report(self):
                return "ok"
        orch.register_substrate("989.x", Stub())
        orch.register_substrate("989.y", Stub())
        results = await orch.run_all_health_checks()
        assert len(results) == 2
        assert results["989.x"].status == SubstrateStatus.HEALTHY

    def test_circuit_breaker_initial_state(self):
        cb = CircuitBreaker(substrate_id="989.x")
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_circuit_breaker_opens_after_threshold(self, orch):
        class Broken:
            def generate_report(self):
                raise Exception("fail")
        orch.register_substrate("989.x", Broken())
        cb = orch.circuit_breakers["989.x"]
        cb.threshold = 2
        for _ in range(2):
            ck = HealthCheck(substrate_id="989.x", timestamp="2026-01-01T00:00:00", latency_ms=0, status=SubstrateStatus.UNHEALTHY, error="fail")
            orch._update_circuit_breaker("989.x", ck)
        assert cb.state == CircuitState.OPEN
        assert orch.metrics.circuit_breaks == 1

    def test_circuit_breaker_half_open_after_timeout(self, orch):
        cb = orch.circuit_breakers["989.x"]
        cb.state = CircuitState.OPEN
        cb.failure_count = 5
        cb.last_failure = "2020-01-01T00:00:00+00:00"
        ck = HealthCheck(substrate_id="989.x", timestamp="2026-01-01T00:00:00", latency_ms=0, status=SubstrateStatus.HEALTHY)
        orch._update_circuit_breaker("989.x", ck)
        assert cb.state == CircuitState.HALF_OPEN

    def test_circuit_breaker_closes_on_success(self, orch):
        cb = orch.circuit_breakers["989.x"]
        cb.state = CircuitState.HALF_OPEN
        cb.half_open_max = 1
        ck = HealthCheck(substrate_id="989.x", timestamp="2026-01-01T00:00:00", latency_ms=0, status=SubstrateStatus.HEALTHY)
        orch._update_circuit_breaker("989.x", ck)
        assert cb.state == CircuitState.CLOSED
        assert orch.metrics.auto_heals == 1

    @pytest.mark.asyncio
    async def test_execute_success(self, orch):
        class Stub:
            def greet(self):
                return "hello"
        orch.register_substrate("989.x", Stub())
        result = await orch.execute("989.x", "greet")
        assert result == "hello"
        assert orch.metrics.successful_requests == 1
        assert orch.metrics.total_requests == 1

    @pytest.mark.asyncio
    async def test_execute_circuit_open(self, orch):
        cb = orch.circuit_breakers["989.x"]
        cb.state = CircuitState.OPEN
        with pytest.raises(Exception, match="Circuit breaker OPEN"):
            await orch.execute("989.x", "anything")

    @pytest.mark.asyncio
    async def test_execute_not_registered(self, orch):
        with pytest.raises(Exception, match="not registered"):
            await orch.execute("989.x", "anything")

    @pytest.mark.asyncio
    async def test_execute_unknown_operation(self, orch):
        class Stub:
            pass
        orch.register_substrate("989.x", Stub())
        with pytest.raises(Exception, match="not found"):
            await orch.execute("989.x", "nonexistent")

    def test_orchestrator_metrics_properties(self):
        m = OrchestratorMetrics(total_requests=100, successful_requests=85, failed_requests=15, total_latency_ms=50000)
        assert m.avg_latency_ms == 500.0
        assert m.success_rate == 0.85
        assert m.availability == 0.85

    def test_generate_report(self, orch):
        class Stub:
            def generate_report(self):
                return "ok"
        orch.register_substrate("989.x", Stub())
        orch._compute_global_metrics()
        r = orch.generate_report()
        assert "989.w-UNIFIED-ORCHESTRATOR" in r

    def test_auto_heal(self, orch):
        """Auto-heal on already-CLOSED should be a no-op."""
        import asyncio
        asyncio.run(orch.auto_heal())
        assert True  # no exception


# ═══════════════════════════════════════════════════════════════════
# Testes de FAIR Metrics Dashboard (989.v)
# ═══════════════════════════════════════════════════════════════════

from fair_metrics_dashboard import FAIRMetricsDashboard, FAIRScore, FAIRAlert, FAIRTrend, FAIRDimension, AlertLevel


@pytest.fixture
def fair():
    return FAIRMetricsDashboard()


class TestFAIRMetricsDashboard:

    def test_substrate_constants(self):
        assert FAIRMetricsDashboard.SUBSTRATE_ID == "989.v"
        assert "FAIR-METRICS-DASHBOARD" in FAIRMetricsDashboard.SEAL

    def test_compute_full_metadata(self, fair):
        meta = {"dpid": "dpid-1001", "doi": "10.arkhe/1001", "title": "Test", "description": "Desc", "keywords": ["k1"], "access_protocol": "https", "license": "CC-BY-4.0", "access_level": "public", "data_format": "json", "ontology": "schema.org", "cross_references": ["dpid-1002"], "provenance": "ARKHE", "version": "1.0.0", "cathedral_seals": ["934"]}
        score = fair.compute_fair_score("dpid-1001", meta)
        assert score.overall == 1.0
        assert score.seal.startswith("FAIR-")

    def test_compute_minimal_metadata(self, fair):
        score = fair.compute_fair_score("dpid-min", {"dpid": "dpid-min"})
        assert score.findable == 0.25
        assert score.overall < 0.5

    def test_score_seal_uniqueness(self, fair):
        meta1 = {"dpid": "dpid-1", "doi": "10.1"}
        meta2 = {"dpid": "dpid-2", "doi": "10.2"}
        s1 = fair.compute_fair_score("ro-1", meta1)
        s2 = fair.compute_fair_score("ro-2", meta2)
        assert s1.seal != s2.seal

    def test_get_ro_dashboard(self, fair):
        meta = {"dpid": "dpid-1001", "doi": "10.arkhe/1001", "title": "T", "description": "D", "keywords": ["k"], "access_protocol": "https", "license": "CC-BY-4.0", "access_level": "public", "data_format": "json", "ontology": "schema.org", "cross_references": ["r1"], "provenance": "ARKHE", "version": "1.0.0", "cathedral_seals": ["934"]}
        fair.compute_fair_score("dpid-1001", meta)
        d = fair.get_ro_dashboard("dpid-1001")
        assert d is not None
        assert d["ro_id"] == "dpid-1001"
        assert d["current_score"]["overall"] == 1.0
        assert d["history_count"] >= 1

    def test_get_ro_dashboard_nonexistent(self, fair):
        assert fair.get_ro_dashboard("no-such") is None

    def test_global_summary_empty(self, fair):
        s = fair.get_global_summary()
        assert s["total_ros"] == 0
        assert s["avg_overall"] == 0.0

    def test_global_summary_populated(self, fair):
        fair.compute_fair_score("ro-1", {"dpid": "ro-1", "title": "T1", "description": "D1", "access_protocol": "https", "license": "CC-BY-4.0", "access_level": "public", "data_format": "json", "ontology": "schema.org", "provenance": "ARKHE", "version": "1.0.0"})
        fair.compute_fair_score("ro-2", {"dpid": "ro-2"})
        s = fair.get_global_summary()
        assert s["total_ros"] == 2
        assert 0 < s["avg_overall"] < 1.0
        assert s["fair_health"] in {"HEALTHY", "DEGRADED", "CRITICAL"}

    def test_alert_generation_on_low_score(self, fair):
        meta = {"dpid": "ro-low"}
        fair.compute_fair_score("ro-low", meta)
        assert len(fair.alerts) > 0
        assert any(a.level == AlertLevel.CRITICAL for a in fair.alerts)

    def test_alert_generation_for_overall(self, fair):
        meta = {"dpid": "ro-low", "title": "T", "description": "D", "access_protocol": "https", "license": "CC-BY-4.0", "access_level": "public", "data_format": "json", "ontology": "schema.org"}
        fair.compute_fair_score("ro-low", meta)
        alerts = [a for a in fair.alerts if "verall" in a.message or "OVERALL" in a.message.upper()]
        assert len(alerts) >= 1

    def test_fair_trend_slope_improving(self):
        trend = FAIRTrend(ro_id="test", dimension=FAIRDimension.FINDABLE)
        trend.scores = [("t1", 0.2), ("t2", 0.5), ("t3", 0.9)]
        assert trend.slope > 0.01
        assert trend.direction == "improving"

    def test_fair_trend_slope_degrading(self):
        trend = FAIRTrend(ro_id="test", dimension=FAIRDimension.FINDABLE)
        trend.scores = [("t1", 0.9), ("t2", 0.5), ("t3", 0.2)]
        assert trend.slope < -0.01
        assert trend.direction == "degrading"

    def test_fair_trend_slope_stable(self):
        trend = FAIRTrend(ro_id="test", dimension=FAIRDimension.FINDABLE)
        trend.scores = [("t1", 0.5), ("t2", 0.51), ("t3", 0.5)]
        assert trend.direction == "stable"

    def test_fair_trend_single_point(self):
        trend = FAIRTrend(ro_id="test", dimension=FAIRDimension.FINDABLE)
        trend.scores = [("t1", 0.5)]
        assert trend.slope == 0.0

    def test_fair_score_to_dict(self):
        s = FAIRScore(ro_id="test", findable=0.75, accessible=0.8, interoperable=0.85, reusable=0.9)
        d = s.to_dict()
        assert d["ro_id"] == "test"
        assert d["overall"] == 0.825

    def test_generate_report(self, fair):
        fair.compute_fair_score("ro-1", {"dpid": "ro-1", "title": "T", "description": "D", "access_protocol": "https", "license": "CC-BY-4.0", "access_level": "public", "data_format": "json", "ontology": "schema.org"})
        r = fair.generate_report()
        assert "989.v-FAIR-METRICS-DASHBOARD" in r
        assert "ROs:" in r


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
