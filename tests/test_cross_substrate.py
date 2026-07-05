# ═══════════════════════════════════════════════════════════════════════════════
# ARKHE OS — Cross-Substrate Service Mesh Tests
# Run: python -m pytest test_cross_substrate.py -v
# ═══════════════════════════════════════════════════════════════════════════════

import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'substrates'))

from substrate_registry import SubstrateRouter, SubstrateGateway, ALL_SUBSTRATES

router = SubstrateRouter()
gateway = SubstrateGateway(router)

def test_registry_contains_core_substrates():
    for sid in ["585", "586", "587", "566", "570", "extenddb"]:
        assert sid in ALL_SUBSTRATES, f"{sid} missing from registry"

def test_all_seals_present():
    for sid, m in ALL_SUBSTRATES.items():
        assert len(m.seal) == 64, f"{sid} seal len={len(m.seal)}"

def test_no_broken_refs():
    errs = router.validate_cross_refs()
    assert errs == {}, f"Broken refs: {errs}"

def test_dag_covers_all():
    dag = router.resolve_dag()
    assert len(dag) == len(ALL_SUBSTRATES)

def test_all_phi_c_above_09():
    for sid, s in router.get_coherence_scores().items():
        assert s["phi_c"] >= 0.90, f"{sid} phi_c={s['phi_c']}"

def test_route_map_has_core():
    routes = router.get_route_map()
    for sid in ["585", "586", "587", "566", "570", "extenddb"]:
        assert sid in routes, f"{sid} missing from route map"

def test_substrate_586_importable():
    from substrates.substrate_586.src.synapse_engine import KuramotoCoherenceEngine, BRODMANN_AREAS, BrodmannMapper
    assert len(BRODMANN_AREAS) == 15
    mapper = BrodmannMapper()
    assert mapper.mni_to_area(-30, -20, 60) == 4

def test_substrate_566_importable():
    from substrates.substrate_566.src.runtime_manager import RuntimeDetector, RuntimeType
    assert RuntimeDetector().PREFERENCE_ORDER[0] == RuntimeType.PODMAN

def test_substrate_570_importable():
    from substrates.substrate_570.src.claude_bridge import ClaudeCodeBridge, PlanStep
    bridge = ClaudeCodeBridge()
    stats = bridge.ingest_codebase(max_tokens=10_000_000)
    assert stats["within_limit"] is True

def test_substrate_585_importable():
    from substrates.substrate_585.groth16_verifier import Groth16Verifier, VerifyingKey, G1Point, G2Point
    vk = VerifyingKey(
        alpha_g1=G1Point(1, 2), beta_g2=G2Point((1, 2), (3, 4)),
        gamma_g2=G2Point((5, 6), (7, 8)), delta_g2=G2Point((9, 10), (11, 12)),
        ic=[G1Point(13, 14)]
    )
    verifier = Groth16Verifier(vk)
    assert verifier is not None

def test_gateway_status_report():
    status = gateway.get_unified_status()
    assert status["status"] == "HEALTHY"
    assert float(status["unified_phi_c"]) >= 0.90

def test_capability_search():
    zk = router.find_by_capability("zk_proof_verify")
    assert "585" in [m.id for m in zk]
    dyn = router.find_by_capability("dynamodb_api")
    assert "extenddb" in [m.id for m in dyn]
    gpu = router.find_by_capability("gpu_inference")
    assert "586" in [m.id for m in gpu]
