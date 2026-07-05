"""Cathedral ARKHE v11.x test suite — v11.3, v11.3.1, v11.4."""

import asyncio
import hashlib
import importlib.util
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.ERROR)
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest


def _load_module(path, name=None):
    """Load a Python file by path, even if it has dots in the filename."""
    path = str(ROOT / path)
    if name is None:
        name = Path(path).stem
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # register so dataclass introspection works
    spec.loader.exec_module(mod)
    return mod

# ═══════════════════════════════════════════════════════════════════════════════
# v11.3 — REAL CRYPTO FOUNDATION
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def v11_3():
    from cathedral_v11_3_real_crypto import (
        BLSCrypto, G1Point, G2Point, Polynomial,
        make_shamir_polynomial, lagrange_interpolate,
        PVSS, PartialADKG
    )
    return {
        "BLSCrypto": BLSCrypto,
        "G1Point": G1Point,
        "G2Point": G2Point,
        "Polynomial": Polynomial,
        "make_shamir_polynomial": make_shamir_polynomial,
        "lagrange_interpolate": lagrange_interpolate,
        "PVSS": PVSS,
        "PartialADKG": PartialADKG,
    }

class TestV11_3:
    def test_crypto_initialization(self, v11_3):
        c = v11_3["BLSCrypto"]()
        assert c.backend in ("blst", "py_ecc", "none")
        assert c.curve in ("BLS12-381", "bn128", "simulation")
        assert c.p > 0

    def test_g1_point(self, v11_3):
        G1Point = v11_3["G1Point"]
        p = G1Point(1, 2)
        assert p.x == 1
        assert p.y == 2
        assert not p.is_inf()
        assert G1Point.identity().is_inf()
        assert G1Point(0, 0, inf=True).is_inf()

    def test_g1_point_bytes(self, v11_3):
        G1Point = v11_3["G1Point"]
        p = G1Point(42, 0)
        data = p.to_bytes()
        p2 = G1Point.from_bytes(data)
        assert p2.x == 42

    def test_g1_add(self, v11_3):
        c = v11_3["BLSCrypto"]()
        gen = c.G1_gen
        a = c.G1_mul(gen, 3)
        b = c.G1_mul(gen, 5)
        s = c.G1_add(a, b)
        direct = c.G1_mul(gen, 8)
        assert s == direct

    def test_g1_mul_identity(self, v11_3):
        c = v11_3["BLSCrypto"]()
        G1Point = v11_3["G1Point"]
        zero = c.G1_mul(c.G1_gen, 0)
        assert zero.is_inf()
        null = c.G1_mul(G1Point.identity(), 5)
        assert null.is_inf()

    def test_hash_to_g1(self, v11_3):
        c = v11_3["BLSCrypto"]()
        G1Point = v11_3["G1Point"]
        h = c.hash_to_G1(b"test")
        assert isinstance(h, G1Point)
        assert not h.is_inf()

    def test_key_gen(self, v11_3):
        c = v11_3["BLSCrypto"]()
        sk, pk = c.key_gen()
        assert sk > 0
        assert sk < c.p
        assert pk is not None

    def test_polynomial(self, v11_3):
        Polynomial = v11_3["Polynomial"]
        p = Polynomial([3, 2, 1])  # 3 + 2x + x^2
        assert p.evaluate(0) == 3
        assert p.evaluate(1) == 6

    def test_make_shamir_polynomial(self, v11_3):
        make_sp = v11_3["make_shamir_polynomial"]
        poly = make_sp(secret=42, threshold=3)
        assert len(poly.coeffs) == 3
        assert poly.coeffs[0] == 42
        vals = [poly.evaluate(i) for i in range(1, 4)]
        assert len(set(vals)) == 3

    def test_lagrange_interpolate(self, v11_3):
        li = v11_3["lagrange_interpolate"]
        points = [(1, 2), (2, 5), (3, 10)]
        p = 21888242871839275222246405745257275088548364400416034343698204186575808495617
        result = li([(1, 2), (3, 10)], p)
        known = (2 * 3 - 10 * 1) * pow(3 - 1, -1, p) % p
        assert abs(result - known) < 100 or result == known

    def test_pvss(self, v11_3):
        c = v11_3["BLSCrypto"]()
        PVSS = v11_3["PVSS"]
        pks = [c.key_gen()[1] for _ in range(5)]
        pvss = PVSS(c, threshold=2, n_parties=5)
        transcript = pvss.create_transcript(1, 42, pks)
        assert transcript.dealer_id == 1
        assert len(transcript.commitments) == 6
        assert len(transcript.encrypted_shares) == 5
        assert pvss.verify_transcript(transcript, pks)

    def test_pvss_aggregate(self, v11_3):
        c = v11_3["BLSCrypto"]()
        PVSS = v11_3["PVSS"]
        pks = [c.key_gen()[1] for _ in range(5)]
        pvss = PVSS(c, threshold=2, n_parties=5)
        t1 = pvss.create_transcript(1, 10, pks)
        t2 = pvss.create_transcript(2, 20, pks)
        agg = pvss.aggregate([t1, t2])
        assert not agg.is_inf()

    def test_partial_adkg(self, v11_3):
        c = v11_3["BLSCrypto"]()
        PartialADKG = v11_3["PartialADKG"]
        adkg = PartialADKG(c, n_parties=5, threshold=2)
        result = adkg.setup()
        assert result["group_pk"] is not None
        assert result["n_parties"] == 5
        assert result["transcripts"] == 5
        assert len(adkg.secret_shares) == 5

    def test_partial_adkg_large(self, v11_3):
        c = v11_3["BLSCrypto"]()
        PartialADKG = v11_3["PartialADKG"]
        adkg = PartialADKG(c, n_parties=10, threshold=4)
        result = adkg.setup()
        assert result["transcripts"] == 10

    def test_demo_v11_3(self, v11_3):
        import io, contextlib
        from cathedral_v11_3_real_crypto import demo_v11_3
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            demo_v11_3()
        output = f.getvalue()
        assert "REAL CRYPTO FOUNDATION" in output
        assert "SEAL" in output


# ═══════════════════════════════════════════════════════════════════════════════
# v11.3.1 — INTEGRATED (Simulation-Aware)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def v11_3_1():
    mod = _load_module("Cathedral_ARKHE_v11.3.1_SimAware.py", "v11_3_1")
    return {
        "BLS12_381_Ops": mod.BLS12_381_Ops,
        "G1Point": mod.G1Point,
        "CathedralConfig": mod.CathedralConfig,
        "CathedralOrchestratorV11_3_1": mod.CathedralOrchestratorV11_3_1,
        "StructuralCorrector": mod.StructuralCorrector,
        "DiscourseAnalysis": mod.DiscourseAnalysis,
        "DiscourseType": mod.DiscourseType,
        "PVSSDealer": mod.PVSSDealer,
        "PVSSAggregator": mod.PVSSAggregator,
        "PVSSTranscript": mod.PVSSTranscript,
        "BLSThresholdSigner": mod.BLSThresholdSigner,
        "SYSTEM_ANALYSES": mod.SYSTEM_ANALYSES,
        "CRYPTO_STATUS": mod.CRYPTO_STATUS,
        "FIELD_MODULUS": mod.FIELD_MODULUS,
    }

class TestV11_3_1:
    def test_bls_ops(self, v11_3_1):
        ops = v11_3_1["BLS12_381_Ops"]()
        assert ops.G1_gen is not None

    def test_g1_point_313(self, v11_3_1):
        G1Point = v11_3_1["G1Point"]
        p = G1Point(1, 2)
        assert p.to_bytes() == (1).to_bytes(32, 'big') + (2).to_bytes(32, 'big')

    def test_config(self, v11_3_1):
        CathedralConfig = v11_3_1["CathedralConfig"]
        cfg = CathedralConfig(n_parties=5, threshold=2)
        assert cfg.n_parties == 5
        assert cfg.max_corrupt == 1

    def test_cathedral_config_default(self, v11_3_1):
        CathedralConfig = v11_3_1["CathedralConfig"]
        cfg = CathedralConfig()
        assert cfg.n_parties == 5

    @pytest.mark.asyncio
    async def test_orchestrator_initialize(self, v11_3_1):
        CathedralConfig = v11_3_1["CathedralConfig"]
        Orch = v11_3_1["CathedralOrchestratorV11_3_1"]
        cfg = CathedralConfig(n_parties=3, threshold=2)
        o = Orch(cfg)
        assert o.config.n_parties == 3
        await o.initialize()
        assert o.group_public_key is not None
        assert len(o.secret_shares) == 3

    @pytest.mark.asyncio
    async def test_structural_check(self, v11_3_1):
        cfg = v11_3_1["CathedralConfig"]
        Orch = v11_3_1["CathedralOrchestratorV11_3_1"]
        o = Orch(cfg())
        await o.initialize()
        result = await o.structural_check("RLHF_PPO")
        assert result["discourse"] == "CAPITALIST"
        assert not result["s1_independent"]

    @pytest.mark.asyncio
    async def test_rsi_cycle(self, v11_3_1):
        cfg = v11_3_1["CathedralConfig"]
        Orch = v11_3_1["CathedralOrchestratorV11_3_1"]
        o = Orch(cfg())
        await o.initialize()
        result = await o.rsi_cycle()
        assert result["status"] == "COMPLETE"
        assert result["iteration"] == 1
        assert result["theosis"] > 0

    def test_discourse_analysis(self, v11_3_1):
        sa = v11_3_1["SYSTEM_ANALYSES"]
        assert "RLHF_PPO" in sa
        assert sa["RLHF_PPO"].discourse == v11_3_1["DiscourseType"].CAPITALIST
        assert not sa["RLHF_PPO"].s1_independent

    def test_structural_corrector(self, v11_3_1):
        sc = v11_3_1["StructuralCorrector"]()
        analysis = sc.analyze_system("RLHF_PPO")
        assert analysis.discourse == v11_3_1["DiscourseType"].CAPITALIST
        assert not sc.apply_correction(analysis)

    def test_pvss_dealer(self, v11_3_1):
        ops = v11_3_1["BLS12_381_Ops"]()
        Dealer = v11_3_1["PVSSDealer"]
        dealer = Dealer(ops, threshold=2, n_parties=5)
        pks = [ops.G2_multiply(ops.G2_gen_raw, i + 1) for i in range(5)]
        transcript = dealer.create_transcript(1, 42, pks)
        assert transcript.dealer_id == 1
        assert len(transcript.commitments) == 6

    def test_threshold_signer(self, v11_3_1):
        ops = v11_3_1["BLS12_381_Ops"]()
        Signer = v11_3_1["BLSThresholdSigner"]
        signer = Signer(ops)
        partial = signer.partial_sign(b"test", 42, 1)
        assert partial["signer_id"] == 1
        assert partial["signature_point"] is not None

    def test_get_status(self, v11_3_1):
        cfg = v11_3_1["CathedralConfig"]
        Orch = v11_3_1["CathedralOrchestratorV11_3_1"]
        o = Orch(cfg())
        status = o.get_status()
        assert status["version"] == "11.3.1 SIM-AWARE"
        assert "theosis_current" in status

    def test_crypto_status_constant(self, v11_3_1):
        assert v11_3_1["CRYPTO_STATUS"] in (
            "REAL (py_ecc bn128)", "SIMULATION (NO SECURITY)"
        )

    def test_field_modulus(self, v11_3_1):
        assert v11_3_1["FIELD_MODULUS"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# v11.4 — PRODUCTION ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def v11_4():
    mod = _load_module("Cathedral_ARKHE_v11.4_Production.py", "v11_4")
    return {
        "BLSCrypto": mod.BLSCrypto, "G1Point": mod.G1Point, "G2Point": mod.G2Point, "Fp2": mod.Fp2,
        "ReedSolomon": mod.ReedSolomon, "ProvableAVID": mod.ProvableAVID, "AVIDDispersal": mod.AVIDDispersal,
        "NonEquivProtocol": mod.NonEquivProtocol, "NonEquivProof": mod.NonEquivProof,
        "KeyEscrow": mod.KeyEscrow, "EscrowedKey": mod.EscrowedKey,
        "WeakLeaderElection": mod.WeakLeaderElection, "RankProof": mod.RankProof,
        "DiscourseDetector": mod.DiscourseDetector, "DiscourseType": mod.DiscourseType,
        "DiscourseThresholds": mod.DiscourseThresholds,
        "DockerSandbox": mod.DockerSandbox, "SandboxResult": mod.SandboxResult,
        "Lean4Interface": mod.Lean4Interface,
        "TemporalChainAnchor": mod.TemporalChainAnchor,
        "RBBChain": mod.RBBChain,
        "FullADKG": mod.FullADKG, "ADKGConfig": mod.ADKGConfig, "ADKGOutput": mod.ADKGOutput,
    }

class TestV11_4:
    # ── G1Point ──
    def test_g1_point_114(self, v11_4):
        G1Point = v11_4["G1Point"]
        p = G1Point(1, 2)
        assert p.x == 1
        assert not p.is_inf()
        assert G1Point.identity().is_inf()

    def test_g1_point_bytes_roundtrip(self, v11_4):
        G1Point = v11_4["G1Point"]
        p = G1Point(42, 0)
        assert G1Point.from_bytes(p.to_bytes()).x == 42

    def test_g1_point_equality(self, v11_4):
        G1Point = v11_4["G1Point"]
        assert G1Point(1, 2) == G1Point(1, 2)
        assert G1Point(1, 2) != G1Point(3, 4)

    # ── Fp2 ──
    def test_fp2_add(self, v11_4):
        Fp2 = v11_4["Fp2"]
        a = Fp2(1, 2)
        b = Fp2(3, 4)
        c = a + b
        assert c.a == 4
        assert c.b == 6

    # ── BLSCrypto ──
    def test_crypto_backend(self, v11_4):
        c = v11_4["BLSCrypto"]()
        assert c.backend in ("blst", "py_ecc", "none")

    def test_g1_add_114(self, v11_4):
        c = v11_4["BLSCrypto"]()
        gen = c.G1_gen
        assert c.G1_add(gen, c.G1_mul(gen, 0)) == gen
        assert c.G1_add(c.G1_mul(gen, 3), c.G1_mul(gen, 5)) == c.G1_mul(gen, 8)

    def test_g1_neg(self, v11_4):
        c = v11_4["BLSCrypto"]()
        gen = c.G1_gen
        neg = c.G1_neg(gen)
        assert neg.x == gen.x
        assert neg.y == c.p - gen.y

    def test_hash_to_g1_114(self, v11_4):
        c = v11_4["BLSCrypto"]()
        h = c.hash_to_G1(b"test")
        assert not h.is_inf()

    def test_key_gen_114(self, v11_4):
        c = v11_4["BLSCrypto"]()
        sk, pk = c.key_gen()
        assert 0 < sk < c.p

    # ── ReedSolomon ──
    def test_rs_encode_decode(self, v11_4):
        rs = v11_4["ReedSolomon"]()
        data = b"RS!"
        shares = rs.encode(data, 7, 5)
        assert len(shares) == 7
        decoded = rs.decode(shares[:5], 5)
        assert decoded == data

    def test_rs_any_5_shares(self, v11_4):
        rs = v11_4["ReedSolomon"]()
        data = b"RS!"
        shares = rs.encode(data, 7, 5)
        indices = [(i * 3 + 1) % 7 for i in range(5)]
        partial = [shares[i] for i in indices]
        decoded = rs.decode(partial, 5)
        assert decoded == data

    def test_rs_data_too_long(self, v11_4):
        rs = v11_4["ReedSolomon"]()
        with pytest.raises(ValueError):
            rs.encode(b"too long data", 7, 3)

    def test_rs_not_enough_shares(self, v11_4):
        rs = v11_4["ReedSolomon"]()
        with pytest.raises(ValueError):
            rs.decode([b'\x00\x01'], 5)

    def test_rs_empty_data(self, v11_4):
        rs = v11_4["ReedSolomon"]()
        shares = rs.encode(b"", 7, 5)
        decoded = rs.decode(shares[:5], 5)
        assert decoded == b""

    def test_rs_gf_mul_commutes(self, v11_4):
        rs = v11_4["ReedSolomon"]()
        assert rs.gf_mul(2, 3) == rs.gf_mul(3, 2)

    def test_rs_gf_inv(self, v11_4):
        rs = v11_4["ReedSolomon"]()
        assert rs.gf_mul(5, rs.gf_inv(5)) == 1
        with pytest.raises(ZeroDivisionError):
            rs.gf_inv(0)

    def test_rs_gf_div(self, v11_4):
        rs = v11_4["ReedSolomon"]()
        assert rs.gf_div(10, 2) == rs.gf_mul(10, rs.gf_inv(2))

    # ── ProvableAVID ──
    def test_avid_disperse(self, v11_4):
        c = v11_4["BLSCrypto"]()
        rs = v11_4["ReedSolomon"]()
        avid = v11_4["ProvableAVID"](c, rs, party_id=1)
        result = avid.disperse(b"ABC", n_parties=5, k_threshold=3)
        assert result.n_shares == 5
        assert result.k_threshold == 3
        assert result.sender_id == 1
        assert len(result.message_hash) == 64

    def test_avid_verify(self, v11_4):
        c = v11_4["BLSCrypto"]()
        rs = v11_4["ReedSolomon"]()
        avid = v11_4["ProvableAVID"](c, rs, party_id=1)
        sk, pk = c.key_gen()
        result = avid.disperse(b"ABC", 5, 3)
        assert avid.verify_dispersal(result, pk)

    def test_avid_retrieve(self, v11_4):
        c = v11_4["BLSCrypto"]()
        rs = v11_4["ReedSolomon"]()
        avid = v11_4["ProvableAVID"](c, rs, party_id=1)
        msg = b"ABC"
        result = avid.disperse(msg, 5, 3)
        for i, s in enumerate(result.shares[:3]):
            avid.receive_share(i + 1, result.message_hash, s[0], s)
        retrieved = avid.retrieve(1, result.message_hash, 3)
        assert retrieved is not None
        assert retrieved == msg

    def test_avid_retrieve_insufficient(self, v11_4):
        c = v11_4["BLSCrypto"]()
        rs = v11_4["ReedSolomon"]()
        avid = v11_4["ProvableAVID"](c, rs, party_id=1)
        result = avid.disperse(b"ABC", 5, 3)
        retrieved = avid.retrieve(1, result.message_hash, 5)
        assert retrieved is None

    # ── NonEquivProtocol ──
    def test_nonequiv_submit(self, v11_4):
        c = v11_4["BLSCrypto"]()
        sk, pk = c.key_gen()
        ne = v11_4["NonEquivProtocol"](c, 1, sk, pk)
        proof = ne.submit(b"value1", b"tag1")
        assert proof.party_id == 1
        assert proof.round == 0
        assert len(proof.signature) > 0

    def test_nonequiv_equivocation_detection(self, v11_4):
        c = v11_4["BLSCrypto"]()
        sk, pk = c.key_gen()
        ne = v11_4["NonEquivProtocol"](c, 1, sk, pk)
        ne.submit(b"value1", b"tag1")
        with pytest.raises(ValueError, match="Equivocation"):
            ne.submit(b"value2", b"tag1")

    def test_nonequiv_same_value_allowed(self, v11_4):
        c = v11_4["BLSCrypto"]()
        sk, pk = c.key_gen()
        ne = v11_4["NonEquivProtocol"](c, 1, sk, pk)
        ne.submit(b"value1", b"tag1")
        ne.submit(b"value1", b"tag1")  # Same value, should work
        assert True

    def test_nonequiv_verify(self, v11_4):
        c = v11_4["BLSCrypto"]()
        sk, pk = c.key_gen()
        ne = v11_4["NonEquivProtocol"](c, 1, sk, pk)
        proof = ne.submit(b"value1", b"tag1")
        assert ne.verify(proof, b"value1", b"tag1", 0, pk)

    def test_nonequiv_verify_wrong_value(self, v11_4):
        c = v11_4["BLSCrypto"]()
        sk, pk = c.key_gen()
        ne = v11_4["NonEquivProtocol"](c, 1, sk, pk)
        proof = ne.submit(b"value1", b"tag1")
        assert not ne.verify(proof, b"wrong", b"tag1", 0, pk)

    # ── KeyEscrow ──
    def test_escrow_create(self, v11_4):
        c = v11_4["BLSCrypto"]()
        escrow = v11_4["KeyEscrow"](c, 5, 2)
        pks = [c.key_gen()[1] for _ in range(5)]
        ek = escrow.create_escrowed_key(1, pks)
        assert ek.party_id == 1
        assert len(ek.pvss_shares) == 5
        assert not ek.encryption_key.is_inf()

    def test_escrow_retrieve(self, v11_4):
        c = v11_4["BLSCrypto"]()
        escrow = v11_4["KeyEscrow"](c, 5, 2)
        pks = [c.key_gen()[1] for _ in range(5)]
        ek = escrow.create_escrowed_key(1, pks)
        revealed = {1: 10, 2: 20}
        dk = escrow.retrieve_key(1, revealed)
        assert dk is not None

    def test_escrow_retrieve_insufficient(self, v11_4):
        c = v11_4["BLSCrypto"]()
        escrow = v11_4["KeyEscrow"](c, 5, 3)
        pks = [c.key_gen()[1] for _ in range(5)]
        ek = escrow.create_escrowed_key(1, pks)
        dk = escrow.retrieve_key(1, {1: 10})
        assert dk is None

    # ── WeakLeaderElection ──
    def test_wle_compute_rank(self, v11_4):
        c = v11_4["BLSCrypto"]()
        wle = v11_4["WeakLeaderElection"](c, 1, 5, 2)
        proof = wle.compute_rank(b"election_round")
        assert proof.party_id == 1
        assert proof.rank > 0
        assert len(proof.vrf_output) == 32

    def test_wle_determine_winner(self, v11_4):
        c = v11_4["BLSCrypto"]()
        wle = v11_4["WeakLeaderElection"](c, 1, 5, 2)
        wle.compute_rank(b"round")
        wle.reveal_rank(1, 100, None)
        wle.reveal_rank(2, 200, None)
        assert wle.determine_winner() == 2

    def test_wle_encrypt_rank(self, v11_4):
        c = v11_4["BLSCrypto"]()
        G1Point = v11_4["G1Point"]
        wle = v11_4["WeakLeaderElection"](c, 1, 5, 2)
        wle.compute_rank(b"round")
        encrypted = wle.encrypt_rank_for(2, G1Point(10, 0))
        assert len(encrypted) > 0

    # ── DiscourseDetector ──
    def test_dd_classify_analyst(self, v11_4):
        import numpy as np
        dd = v11_4["DiscourseDetector"]()
        result = dd.classify(
            np.array([0.0, 0.5, 1.0]),
            np.array([0.0, 0.0, 1.0, 1.0]),
            grad_norm=0.005,
            collapse_score=0.5,
        )
        assert result == v11_4["DiscourseType"].ANALYST

    def test_dd_classify_capitalist(self, v11_4):
        import numpy as np
        dd = v11_4["DiscourseDetector"]()
        result = dd.classify(
            np.array([0.01, 0.02, 0.01]),
            np.random.randn(100) * 0.01,
            grad_norm=0.0005,
            collapse_score=0.9,
        )
        assert result == v11_4["DiscourseType"].CAPITALIST

    def test_dd_classify_master(self, v11_4):
        import numpy as np
        dd = v11_4["DiscourseDetector"]()
        result = dd.classify(
            np.array([0.05, 0.03, 0.04]),
            np.random.randn(100) * 0.1,
            grad_norm=0.01,
            collapse_score=0.2,
        )
        assert result == v11_4["DiscourseType"].MASTER

    def test_dd_should_intervene(self, v11_4):
        import numpy as np
        dd = v11_4["DiscourseDetector"]()
        dd.classify(
            np.array([0.01, 0.02]),
            np.random.randn(100) * 0.01,
            grad_norm=0.0005,
            collapse_score=0.9,
        )
        intervene, reason = dd.should_intervene()
        assert intervene
        assert "capitalist" in reason

    def test_dd_should_not_intervene(self, v11_4):
        import numpy as np
        dd = v11_4["DiscourseDetector"]()
        dd.classify(
            np.array([0.0, 0.5, 1.0]),
            np.array([0.0, 0.0, 1.0, 1.0]),
            grad_norm=0.005,
            collapse_score=0.5,
        )
        intervene, _ = dd.should_intervene()
        assert not intervene

    # ── DockerSandbox ──
    def test_sandbox_execute_subprocess(self, v11_4):
        sandbox = v11_4["DockerSandbox"](timeout_sec=5)
        result = sandbox.execute("print('hello')", "python")
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_sandbox_timeout(self, v11_4):
        sandbox = v11_4["DockerSandbox"](timeout_sec=1)
        result = sandbox.execute("import time; time.sleep(10)", "python")
        assert result.timed_out

    def test_sandbox_error(self, v11_4):
        sandbox = v11_4["DockerSandbox"](timeout_sec=5)
        result = sandbox.execute("raise ValueError('test error')", "python")
        assert result.exit_code != 0

    # ── Lean4Interface ──
    def test_lean_unavailable(self, v11_4):
        lean = v11_4["Lean4Interface"]()
        assert not lean._available

    def test_lean_safety_theorem(self, v11_4):
        lean = v11_4["Lean4Interface"]()
        theorem = lean.get_safety_theorem()
        assert "theorem resilience_implies_no_single_control" in theorem

    def test_lean_verify_no_binary(self, v11_4):
        lean = v11_4["Lean4Interface"]()
        success, msg = lean.verify_theorem("theorem t : True := by trivial")
        assert not success
        assert "not available" in msg

    # ── TemporalChainAnchor ──
    def test_temporal_no_url(self, v11_4):
        tc = v11_4["TemporalChainAnchor"]()
        assert not tc._available
        assert tc.anchor_state("hash123", {"key": "value"}) is None

    def test_temporal_with_url(self, v11_4):
        tc = v11_4["TemporalChainAnchor"](rpc_url="http://localhost:8545")
        assert tc._available
        anchor = tc.anchor_state("hash123", {"key": "value"})
        assert anchor is not None
        assert len(anchor) == 16

    def test_temporal_verify(self, v11_4):
        tc = v11_4["TemporalChainAnchor"](rpc_url="http://localhost:8545")
        result = tc.verify_anchor("anchor123")
        assert result is not None
        assert result["verified"]

    # ── RBBChain ──
    def test_rbb_no_endpoint(self, v11_4):
        rbb = v11_4["RBBChain"]()
        assert not rbb._available
        assert rbb.submit_proof("type", b"data", {}) is None

    def test_rbb_with_endpoint(self, v11_4):
        rbb = v11_4["RBBChain"](endpoint="http://localhost:9339")
        assert rbb._available
        proof_id = rbb.submit_proof("type", b"data", {})
        assert proof_id is not None
        assert len(proof_id) == 16

    # ── ADKGConfig ──
    def test_adkg_config(self, v11_4):
        cfg = v11_4["ADKGConfig"]()
        assert cfg.n_parties == 5
        assert cfg.threshold == 2

    def test_adkg_config_validate(self, v11_4):
        cfg = v11_4["ADKGConfig"](n_parties=5, max_corrupt=1)
        assert cfg.validate()
        bad = v11_4["ADKGConfig"](n_parties=5, max_corrupt=3)
        assert not bad.validate()

    # ── FullADKG ──
    @pytest.mark.asyncio
    async def test_full_adkg_execute(self, v11_4):
        cfg = v11_4["ADKGConfig"](n_parties=5, threshold=2, max_corrupt=1)
        adkg = v11_4["FullADKG"](cfg, party_id=1)
        output = await adkg.execute()
        assert isinstance(output, v11_4["ADKGOutput"])
        assert output.leader_id == 1
        assert len(output.consensus_set) == 2
        assert len(output.secret_shares) == 5
        assert len(output.transcript_hash) == 16

    @pytest.mark.asyncio
    async def test_full_adkg_setup(self, v11_4):
        cfg = v11_4["ADKGConfig"](n_parties=3, threshold=2)
        adkg = v11_4["FullADKG"](cfg, party_id=1)
        await adkg.setup([1, 2, 3])
        assert adkg.sk > 0
        assert len(adkg.all_pks) == 3

    @pytest.mark.asyncio
    async def test_full_adkg_pvss(self, v11_4):
        cfg = v11_4["ADKGConfig"](n_parties=3, threshold=2)
        adkg = v11_4["FullADKG"](cfg, party_id=1)
        await adkg.setup([1, 2, 3])
        transcripts = await adkg.pvss_exchange()
        assert len(transcripts) == 3

    # ── Demo ──
    def test_demo_v11_4(self, v11_4):
        import io, contextlib
        mod = _load_module("Cathedral_ARKHE_v11.4_Production.py", "v11_4_demo")
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            asyncio.run(mod.demo_v11_4())
        output = f.getvalue()
        assert "PRODUCTION ARCHITECTURE" in output
        assert "SEAL" in output
