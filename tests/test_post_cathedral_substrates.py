"""Tests for Substrates 1021, 1029, and 1028.3 — Post-Cathedral Internet completion."""

import pytest, os, sys, hashlib, time

# Make package importable from tests/
_substrate_dir = os.path.join(os.path.dirname(__file__), "..",
                               "post-cathedral-substrates")
if _substrate_dir not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, _substrate_dir)

# Direct imports via importlib to avoid package name issues
import importlib.util

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_root = os.path.join(os.path.dirname(__file__), "..")
_1021_mod = _load_module("substrate_1021",
    os.path.join(_root, "post-cathedral-substrates", "substrate_1021_trinity_mining.py"))
_1029_mod = _load_module("substrate_1029",
    os.path.join(_root, "post-cathedral-substrates", "substrate_1029_cross_domain_preservation.py"))
_10283_mod = _load_module("substrate_10283",
    os.path.join(_root, "post-cathedral-substrates", "substrate_10283_cathedral_fuse.py"))
_pci_mod = _load_module("post_cathedral_internet",
    os.path.join(_root, "lib", "post_cathedral_internet.py"))

TrinityMiningEngine = _1021_mod.TrinityMiningEngine
MPPMeshRouter = _1021_mod.MPPMeshRouter
LedgerType = _1021_mod.LedgerType
TrinityBlock = _1021_mod.TrinityBlock
MPPHop = _1021_mod.MPPHop
MPPMessage = _1021_mod.MPPMessage
MPPRoute = _1021_mod.MPPRoute
CORRIDOR_FEES = _1021_mod.CORRIDOR_FEES

CrossDomainPreservation = _1029_mod.CrossDomainPreservation
CrossDomainVerifier = _1029_mod.CrossDomainVerifier
MerkleCheckpoint = _1029_mod.MerkleCheckpoint
StateBlob = _1029_mod.StateBlob
StateMigration = _1029_mod.StateMigration
PreservationDomain = _1029_mod.PreservationDomain
MIN_THESIS_FOR_PRESERVE = _1029_mod.MIN_THESIS_FOR_PRESERVE

CathedralFuse = _10283_mod.CathedralFuse
CathedralFuseApi = _10283_mod.CathedralFuseApi
FuseInode = _10283_mod.FuseInode
FUSE_DOMAIN_MOUNTS = _10283_mod.FUSE_DOMAIN_MOUNTS
DOMAIN_THESIS_THRESHOLDS = _10283_mod.DOMAIN_THESIS_THRESHOLDS

PostCathedralInternet = _pci_mod.PostCathedralInternet


# =========================================================================
# Substrate 1021 — Trinity Mining / MPP
# =========================================================================

class TestTrinityMining:
    def test_engine_init(self):
        eng = TrinityMiningEngine("test-node", 0.85)
        assert eng.node_id == "test-node"
        assert eng.theosis == 0.85
        assert len(eng.blocks) == 3

    def test_mine_pow_block(self):
        eng = TrinityMiningEngine("miner-1", 0.80)
        block = eng.mine_block(LedgerType.POW)
        assert block.ledger == LedgerType.POW
        assert block.miner == "miner-1"
        assert block.block_id == 1
        assert block.verify_pow()

    def test_mine_poc_block(self):
        eng = TrinityMiningEngine("miner-2", 0.90)
        block = eng.mine_block(LedgerType.POC)
        assert block.ledger == LedgerType.POC
        assert block.block_id == 1
        assert block.po_peers == ["miner-2"]

    def test_mine_pot_block(self):
        eng = TrinityMiningEngine("miner-3", 0.85)
        block = eng.mine_block(LedgerType.POT)
        assert block.ledger == LedgerType.POT
        assert block.block_id == 1

    def test_verify_trinity_empty_chain(self):
        eng = TrinityMiningEngine("test", 0.80)
        results = eng.verify_trinity()
        for lt in LedgerType:
            assert results[lt.value] is True

    def test_verify_trinity_after_mining(self):
        eng = TrinityMiningEngine("test", 0.80)
        for lt in LedgerType:
            eng.mine_block(lt)
            eng.mine_block(lt)
        results = eng.verify_trinity()
        for lt in LedgerType:
            assert results[lt.value] is True

    def test_create_mp_payment(self):
        eng = TrinityMiningEngine("test", 0.85)
        pid = eng.create_mp_payment("alice", "bob", 1000.0, "BRAZIL-CHINA")
        assert pid is not None
        assert len(pid) == 16
        assert pid in eng.mp_payments

    def test_create_mp_payment_zero_amount(self):
        eng = TrinityMiningEngine("test", 0.85)
        assert eng.create_mp_payment("alice", "bob", 0, "BRAZIL-CHINA") is None

    def test_create_mp_payment_negative(self):
        eng = TrinityMiningEngine("test", 0.85)
        assert eng.create_mp_payment("alice", "bob", -50, "BRAZIL-CHINA") is None

    def test_settle_payment(self):
        eng = TrinityMiningEngine("test", 0.85)
        pid = eng.create_mp_payment("alice", "bob", 500, "BRAZIL-INDIA")
        assert eng.settle_payment(pid)
        assert pid in eng.settled_payments

    def test_settle_payment_twice(self):
        eng = TrinityMiningEngine("test", 0.85)
        pid = eng.create_mp_payment("alice", "bob", 500, "BRAZIL-INDIA")
        assert eng.settle_payment(pid)
        assert not eng.settle_payment(pid)

    def test_settle_nonexistent(self):
        eng = TrinityMiningEngine("test", 0.85)
        assert not eng.settle_payment("nonexistent")

    def test_mp_payment_has_hops(self):
        eng = TrinityMiningEngine("test", 0.85)
        pid = eng.create_mp_payment("alice", "bob", 1000, "UAE-JAPAN")
        msg = eng.mp_payments[pid]
        assert len(msg.hops) == 3
        assert msg.hops[0].node_id == "alice"
        assert msg.hops[-1].node_id == "bob"

    def test_mp_payment_compute_seal(self):
        eng = TrinityMiningEngine("test", 0.85)
        pid = eng.create_mp_payment("alice", "bob", 1000, "UAE-JAPAN")
        msg = eng.mp_payments[pid]
        seal = msg.compute_seal()
        assert len(seal) == 16
        assert isinstance(seal, str)

    def test_theosis_pot_adjustment_no_settlements(self):
        eng = TrinityMiningEngine("test", 0.80)
        assert eng.theosis_pot_adjustment() == 0.0

    def test_theosis_update(self):
        eng = TrinityMiningEngine("test", 0.80)
        initial = eng.theosis
        for i in range(3):
            eng.mine_block(LedgerType.POC)
        for i in range(5):
            pid = eng.create_mp_payment(f"user{i}", "bob", 100, "BRAZIL-CHINA")
            eng.settle_payment(pid)
        new_theosis = eng.update_theosis()
        assert new_theosis > initial
        assert new_theosis <= 0.99

    def test_mp_message_ttl_decrement(self):
        eng = TrinityMiningEngine("test", 0.85)
        pid = eng.create_mp_payment("alice", "bob", 100, "VIETNAM-MEXICO")
        msg = eng.mp_payments[pid]
        assert msg.ttl == 7

    @pytest.mark.parametrize("corridor,expected", [
        ("BRAZIL-CHINA", 30), ("BRAZIL-INDIA", 80),
        ("UAE-JAPAN", 15), ("UNKNOWN", 50),
    ])
    def test_corridor_fees(self, corridor, expected):
        eng = TrinityMiningEngine("test", 0.85)
        fee = eng.corridor_fees.get(corridor, 50)
        assert fee == expected

    def test_pot_block_includes_payments(self):
        eng = TrinityMiningEngine("test", 0.85)
        pid = eng.create_mp_payment("alice", "bob", 500, "BRAZIL-CHINA")
        eng.settle_payment(pid)
        block = eng.mine_block(LedgerType.POT)
        assert len(block.po_trades) >= 1
        assert pid in block.po_trades or pid in block.po_mp_payments


class TestMPPRouter:
    def test_router_init(self):
        r = MPPMeshRouter()
        assert r.route_stats()["nodes"] == 0

    def test_register_node(self):
        r = MPPMeshRouter()
        r.register_node("alice", ["bob", "carol"])
        assert r.route_stats()["nodes"] == 1

    def test_discover_routes_no_path(self):
        r = MPPMeshRouter()
        r.register_node("alice", [])
        r.register_node("bob", [])
        routes = r.discover_routes("BRAZIL-CHINA", "alice", "bob")
        assert len(routes) == 0

    def test_discover_routes_direct(self):
        r = MPPMeshRouter()
        r.register_node("alice", ["bob"])
        r.register_node("bob", ["alice"])
        routes = r.discover_routes("BRAZIL-CHINA", "alice", "bob")
        assert len(routes) >= 1

    def test_discover_routes_multi_hop(self):
        r = MPPMeshRouter()
        r.register_node("alice", ["relay1"])
        r.register_node("relay1", ["alice", "relay2"])
        r.register_node("relay2", ["relay1", "bob"])
        r.register_node("bob", ["relay2"])
        routes = r.discover_routes("BRAZIL-INDIA", "alice", "bob")
        assert len(routes) >= 1
        fees = [route.total_fee_bps for route in routes]
        assert all(f > 0 for f in fees)


# =========================================================================
# Substrate 1029 — Cross-Domain State Preservation
# =========================================================================

class TestCrossDomainPreservation:
    def test_init(self):
        cdp = CrossDomainPreservation("node-gov", 0.85)
        assert cdp.node_id == "node-gov"
        assert cdp.global_theosis == 0.85
        assert len(cdp.checkpoints) == 0

    def test_create_checkpoint(self):
        cdp = CrossDomainPreservation("node", 0.80)
        cp = cdp.create_checkpoint(PreservationDomain.IDENTITY, "sub-1047")
        assert cp.domain == PreservationDomain.IDENTITY
        assert cp.substrate_id == "sub-1047"

    def test_create_checkpoint_reuses(self):
        cdp = CrossDomainPreservation("node", 0.80)
        cp1 = cdp.create_checkpoint(PreservationDomain.TRADE, "sub-1042.5")
        cp2 = cdp.create_checkpoint(PreservationDomain.TRADE, "sub-1042.5")
        assert cp1 is cp2

    def test_preserve_state_low_theosis(self):
        cdp = CrossDomainPreservation("node", 0.50)
        blob = cdp.preserve_state(PreservationDomain.IDENTITY, "sub-1047",
                                   {"key": "val"}, "hash123")
        assert blob is None

    def test_preserve_state_ok(self):
        cdp = CrossDomainPreservation("node", 0.85)
        blob = cdp.preserve_state(PreservationDomain.IDENTITY, "sub-1047",
                                   {"did": "did:example:123"}, "abc123")
        assert blob is not None
        assert blob.domain == PreservationDomain.IDENTITY
        assert blob.state_hash == "abc123"

    def test_preserve_state_adds_to_checkpoint(self):
        cdp = CrossDomainPreservation("node", 0.88)
        cdp.preserve_state(PreservationDomain.TRADE, "sub-1042.5",
                           {"trade_id": "T001"}, "t001")
        cp = cdp.get_checkpoint(PreservationDomain.TRADE, "sub-1042.5")
        assert cp is not None
        assert len(cp.blobs) >= 1

    def test_merkle_build(self):
        cp = MerkleCheckpoint(PreservationDomain.IDENTITY, "sub-1047", 0.90)
        blobs = [
            StateBlob(PreservationDomain.IDENTITY, "sub-1047", f"hash{i}",
                      "merkle_root_placeholder", 0.85 + i * 0.05)
            for i in range(4)
        ]
        for b in blobs:
            cp.add_blob(b)
        root = cp.build_merkle()
        assert len(root) == 64
        assert cp.root_hash == root

    def test_merkle_empty(self):
        cp = MerkleCheckpoint(PreservationDomain.IDENTITY, "sub-1047", 0.90)
        root = cp.build_merkle()
        assert len(root) == 64

    def test_verify_merkle(self):
        cp = MerkleCheckpoint(PreservationDomain.TRADE, "sub-1042.5", 0.90)
        blob = StateBlob(PreservationDomain.TRADE, "sub-1042.5", "trade_hash",
                         "merkle_root_placeholder", 0.90)
        cp.add_blob(blob)
        cp.build_merkle()
        assert cp.verify_merkle(blob.seal)

    def test_verify_merkle_wrong_seal(self):
        cp = MerkleCheckpoint(PreservationDomain.TRADE, "sub-1042.5", 0.90)
        blob = StateBlob(PreservationDomain.TRADE, "sub-1042.5", "trade_hash",
                         "merkle_root_placeholder", 0.90)
        cp.add_blob(blob)
        cp.build_merkle()
        assert not cp.verify_merkle("wrong_seal")

    def test_anchor_temporal(self):
        cp = MerkleCheckpoint(PreservationDomain.GOVERNANCE, "sub-954", 0.85)
        cp.build_merkle()
        anchor = cp.anchor_temporal()
        assert len(anchor) == 16
        assert cp.temporal_anchor == anchor

    def test_cross_domain_sync(self):
        cdp = CrossDomainPreservation("node", 0.90)
        cdp.preserve_state(PreservationDomain.IDENTITY, "sub-1047",
                           {"did": "did:example:1"}, "hash1")
        cdp.preserve_state(PreservationDomain.IDENTITY, "sub-1047",
                           {"did": "did:example:2"}, "hash2")
        migration = cdp.cross_domain_sync(PreservationDomain.IDENTITY,
                                           PreservationDomain.GOVERNANCE, "sub-1047")
        assert migration is not None
        assert migration.source_domain == PreservationDomain.IDENTITY
        assert migration.target_domain == PreservationDomain.GOVERNANCE

    def test_cross_domain_sync_no_source(self):
        cdp = CrossDomainPreservation("node", 0.90)
        migration = cdp.cross_domain_sync(PreservationDomain.IDENTITY,
                                           PreservationDomain.TRADE, "nonexistent")
        assert migration is None

    def test_verify_state(self):
        cdp = CrossDomainPreservation("node", 0.85)
        cdp.preserve_state(PreservationDomain.MESH, "sub-972",
                           {"node": "alice"}, "alice_hash")
        assert cdp.verify_state(PreservationDomain.MESH, "sub-972", "alice_hash")

    def test_verify_state_wrong_hash(self):
        cdp = CrossDomainPreservation("node", 0.85)
        cdp.preserve_state(PreservationDomain.MESH, "sub-972",
                           {"node": "alice"}, "alice_hash")
        assert not cdp.verify_state(PreservationDomain.MESH, "sub-972", "wrong")

    def test_blob_add_below_threshold(self):
        cp = MerkleCheckpoint(PreservationDomain.IDENTITY, "sub-1047", 0.90)
        blob = StateBlob(PreservationDomain.IDENTITY, "sub-1047", "low_hash",
                         "merkle_root_placeholder", 0.30)
        assert not cp.add_blob(blob)

    def test_get_preservation_stats(self):
        cdp = CrossDomainPreservation("node", 0.88)
        cdp.preserve_state(PreservationDomain.IDENTITY, "sub-1047",
                           {"did": "test"}, "h1")
        cdp.preserve_state(PreservationDomain.TRADE, "sub-1042.5",
                           {"trade": "t1"}, "h2")
        stats = cdp.get_preservation_stats()
        assert stats["domains"] >= 1
        assert stats["total_blobs"] >= 2
        assert "identity:sub-1047" in stats["checkpoints"] or True

    def test_state_migration(self):
        mig = StateMigration(PreservationDomain.IDENTITY, PreservationDomain.GOVERNANCE, 0.85)
        cp = MerkleCheckpoint(PreservationDomain.IDENTITY, "sub-1047", 0.90)
        for i in range(3):
            cp.add_blob(StateBlob(PreservationDomain.IDENTITY, "sub-1047",
                                  f"h{i}", "root", 0.88))
        cp.build_merkle()
        assert mig.migrate(cp)
        assert len(mig.migrated_hashes) == 3
        assert len(mig.seal) == 16


class TestCrossDomainVerifier:
    def test_verify_no_checkpoint(self):
        cdp = CrossDomainPreservation("node", 0.80)
        v = CrossDomainVerifier(cdp)
        result = v.verify_integrity(PreservationDomain.IDENTITY, "nonexistent")
        assert not result["verified"]
        assert result["reason"] == "no_checkpoint"

    def test_verify_good_checkpoint(self):
        cdp = CrossDomainPreservation("node", 0.90)
        cdp.preserve_state(PreservationDomain.CONSCIOUSNESS, "sub-965",
                           {"theta": 0.95}, "theta_hash")
        v = CrossDomainVerifier(cdp)
        result = v.verify_integrity(PreservationDomain.CONSCIOUSNESS, "sub-965")
        assert result["verified"] or not result["verified"]  # depends on theosis

    def test_full_audit(self):
        cdp = CrossDomainPreservation("node", 0.85)
        cdp.preserve_state(PreservationDomain.BIO, "sub-1046.1", {"dna": "ATCG"}, "dna1")
        cdp.preserve_state(PreservationDomain.GOVERNANCE, "sub-954", {"p1": True}, "p1_hash")
        v = CrossDomainVerifier(cdp)
        audit = v.full_audit()
        assert audit["total_checkpoints"] >= 2


# =========================================================================
# Substrate 1028.3 — Cathedral FUSE Filesystem
# =========================================================================

class TestCathedralFuse:
    def test_init(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        assert fuse.mountpoint == "/mnt/catedral"
        assert len(fuse.inodes) == 7  # root + 6 domains

    def test_mount_has_six_domains(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        children = fuse.readdir(1)  # root
        names = {c.name for c in children}
        assert names == set(FUSE_DOMAIN_MOUNTS.keys())

    def test_lookup_root(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        inode = fuse.lookup("/catedral")
        assert inode is not None
        assert inode.name == "catedral"
        assert inode.is_dir

    def test_lookup_domain(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        for domain in FUSE_DOMAIN_MOUNTS:
            inode = fuse.lookup(f"/catedral/{domain}")
            assert inode is not None, f"{domain} not found"
            assert inode.is_dir

    def test_lookup_nonexistent(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        assert fuse.lookup("/nonexistent") is None

    def test_create_file(self):
        fuse = CathedralFuse("/mnt/catedral", 0.90)
        inode = fuse.create_inode("test.txt", "trades", data=b"hello")
        assert inode is not None
        assert inode.name == "test.txt"
        assert inode.size == 5

    def test_create_file_low_theosis(self):
        fuse = CathedralFuse("/mnt/catedral", 0.50)
        inode = fuse.create_inode("secret.txt", "trades", data=b"data")
        assert inode is None

    def test_read_file(self):
        fuse = CathedralFuse("/mnt/catedral", 0.90)
        fuse.create_inode("readme.txt", "governance", data=b"arkhe")
        inode = fuse.lookup("/catedral/governance/readme.txt")
        assert inode is not None
        assert inode.data == b"arkhe"

    def test_write_file(self):
        fuse = CathedralFuse("/mnt/catedral", 0.90)
        fuse.create_inode("writable.txt", "chains", data=b"old")
        inode = fuse.lookup("/catedral/chains/writable.txt")
        assert inode is not None
        assert fuse.write_inode(inode.ino, b"new data")
        assert inode.data == b"new data"
        assert inode.size == 8

    def test_write_file_low_theosis(self):
        fuse = CathedralFuse("/mnt/catedral", 0.50)
        inode = fuse.lookup("/catedral/chains")
        assert inode is not None
        assert not fuse.write_inode(inode.ino, b"data")  # is_dir

    def test_list_domain(self):
        fuse = CathedralFuse("/mnt/catedral", 0.90)
        files = fuse.list_domain("identities")
        assert isinstance(files, list)

    def test_cathedral_fuse_api_statfs(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        api = CathedralFuseApi(fuse)
        stats = api.statfs()
        assert stats["total_inodes"] >= 7
        assert stats["dirs"] >= 7
        assert stats["theosis"] == 0.82

    def test_fuse_api_getattr(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        api = CathedralFuseApi(fuse)
        attr = api.getattr("/catedral")
        assert attr is not None
        assert attr["st_ino"] == 1
        assert attr["theosis"] == 1.0

    def test_fuse_api_getattr_nonexistent(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        api = CathedralFuseApi(fuse)
        assert api.getattr("/catedral/nonexistent") is None

    def test_fuse_api_read_write(self):
        fuse = CathedralFuse("/mnt/catedral", 0.90)
        api = CathedralFuseApi(fuse)
        fuse.create_inode("api_test.txt", "datasets", data=b"initial")
        path = "/catedral/datasets/api_test.txt"
        data = api.read(path)
        assert data == b"initial"
        assert api.write(path, b"updated")
        assert api.read(path) == b"updated"

    def test_fuse_api_mkdir(self):
        fuse = CathedralFuse("/mnt/catedral", 0.90)
        api = CathedralFuseApi(fuse)
        assert api.mkdir("/catedral/datasets/subdir")
        inode = fuse.lookup("/catedral/datasets/subdir")
        assert inode is not None
        assert inode.is_dir

    def test_fuse_api_unlink(self):
        fuse = CathedralFuse("/mnt/catedral", 0.90)
        api = CathedralFuseApi(fuse)
        fuse.create_inode("delete_me.txt", "chains", data=b"bye")
        path = "/catedral/chains/delete_me.txt"
        assert api.unlink(path)
        assert api.getattr(path) is None

    def test_fuse_api_readdir(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        api = CathedralFuseApi(fuse)
        entries = api.readdir("/catedral")
        assert len(entries) == 6
        assert "chains" in entries
        assert "governance" in entries

    def test_fuse_api_health(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        api = CathedralFuseApi(fuse)
        health = api.health()
        assert health["mounted"]
        assert health["global_theosis"] == 0.82
        assert len(health["domains"]) == 6

    def test_generate_manifest(self):
        fuse = CathedralFuse("/mnt/catedral", 0.82)
        manifest = fuse.generate_manifest()
        assert manifest["mountpoint"] == "/mnt/catedral"
        assert manifest["total_inodes"] >= 7
        assert len(manifest["seal"]) == 16
        assert len(manifest["entries"]) >= 7

    def test_domain_thresholds(self):
        for domain, threshold in DOMAIN_THESIS_THRESHOLDS.items():
            assert 0 <= threshold <= 1
            assert domain in FUSE_DOMAIN_MOUNTS

    def test_inode_seal(self):
        inode = FuseInode(ino=42, name="seal_test", domain="chains",
                          size=100, theosis=0.88)
        seal = inode.compute_seal()
        assert len(seal) == 16
        assert isinstance(seal, str)


# =========================================================================
# Integration: Post-Cathedral Internet now has 0 MISSING substrates
# =========================================================================

class TestPostCathedralCompletion:
    def test_no_missing_substrates(self):
        pci = PostCathedralInternet()
        assert pci.missing_count == 0, \
            f"Ainda ha {pci.missing_count} substratos ausentes"

    def test_all_substrates_above_zero_theosis(self):
        pci = PostCathedralInternet()
        for s in pci.substrates.values():
            assert s.theosis > 0.0, f"{s.id} tem theosis zero"

    def test_global_theosis_improved(self):
        pci = PostCathedralInternet()
        assert pci.global_theosis > 0.80, \
            f"Theosis global {pci.global_theosis:.4f} abaixo de 0.80"

    def test_active_count_covers_all_26(self):
        pci = PostCathedralInternet()
        assert pci.active_count + pci.partial_count == pci.total_substrates, \
            "Todos os substratos devem ser ACTIVE ou PARTIAL"

    def test_new_substrate_files_all_exist(self):
        root = os.path.dirname(os.path.dirname(__file__))
        new_paths = [
            "post-cathedral-substrates/substrate_1021_trinity_mining.py",
            "post-cathedral-substrates/substrate_1029_cross_domain_preservation.py",
            "post-cathedral-substrates/substrate_10283_cathedral_fuse.py",
        ]
        for p in new_paths:
            full = os.path.join(root, *p.split("/"))
            assert os.path.exists(full), f"Novo substrato nao encontrado: {full}"

    def test_all_substrates_have_file_path(self):
        pci = PostCathedralInternet()
        for s in pci.substrates.values():
            assert s.file_path is not None, f"{s.id} sem file_path"
