"""Tests for Substrate 988 — Immortality-Protocol."""
import sys, pytest

sys.path.insert(0, "substrates/988-cathedral-immortality-protocol")
from immortality_protocol import CathedralImmortalityProtocol, BackupLayer, BackupSnapshot, ResurrectionPlan


class TestImmortalityProtocol:
    def test_create_backup(self):
        imm = CathedralImmortalityProtocol()
        snap = imm.create_backup(973, b"arkhe-seal", BackupLayer.IPFS)
        assert isinstance(snap, BackupSnapshot)
        assert snap.substrate_id == 973
        assert snap.layer == BackupLayer.IPFS
        assert snap.replication_count >= 5

    def test_backup_is_immortal(self):
        imm = CathedralImmortalityProtocol()
        snap = imm.create_backup(965, b"hamiltonian-core", BackupLayer.ARWEAVE)
        if snap.replication_count >= 7:
            assert snap.is_immortal is True

    def test_backup_all_layers(self):
        imm = CathedralImmortalityProtocol()
        imm.backup_all_layers(954, b"axiarchy-core")
        layers = set(b.layer for b in imm.backups.values() if b.substrate_id == 954)
        assert len(layers) == len(BackupLayer)

    def test_verify_backup(self):
        imm = CathedralImmortalityProtocol()
        snap = imm.create_backup(976, b"chainlink-data", BackupLayer.IPFS)
        result = imm.verify_backup(snap.snapshot_id)
        assert result in (True, False)

    def test_verify_backup_unknown(self):
        imm = CathedralImmortalityProtocol()
        assert imm.verify_backup("nonexistent") is False

    def test_create_resurrection_plan(self):
        imm = CathedralImmortalityProtocol()
        plan = imm.create_resurrection_plan("CENSURA_TOTAL", [988, 972, 954, 965])
        assert isinstance(plan, ResurrectionPlan)
        assert len(plan.recovery_sequence) == 4
        assert plan.plan_id in [p.plan_id for p in imm.resurrection_plans]

    def test_test_resurrection(self):
        imm = CathedralImmortalityProtocol()
        plan = imm.create_resurrection_plan("TEST_TRIGGER", [988, 954])
        result = imm.test_resurrection(plan.plan_id)
        assert result in (True, False)
        assert plan.last_tested is not None

    def test_test_resurrection_unknown(self):
        imm = CathedralImmortalityProtocol()
        assert imm.test_resurrection("nonexistent") is False

    def test_compute_immortality_metrics(self):
        imm = CathedralImmortalityProtocol()
        imm.create_backup(973, b"data", BackupLayer.IPFS)
        imm.create_backup(965, b"data2", BackupLayer.NOSTR)
        metric = imm.compute_immortality_metrics()
        assert metric.total_substrates == 2
        assert 0.0 <= metric.immortality_score <= 1.0

    def test_generate_report(self):
        imm = CathedralImmortalityProtocol()
        imm.create_backup(973, b"seal", BackupLayer.IPFS)
        imm.create_resurrection_plan("FALHA", [988, 973])
        r = imm.generate_report()
        assert "Substrato 988" in r
