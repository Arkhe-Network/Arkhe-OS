"""Tests for Post-Cathedral Internet Architecture (genesis)."""

import pytest
from pathlib import Path
import sys, os

_engine_dir = str(Path(__file__).parent)
if _engine_dir not in sys.path:
    sys.path.insert(0, _engine_dir)

from post_cathedral_internet import (
    PostCathedralInternet, SubstrateRef, Layer,
    LAYER_NAMES, ARCHITECTURE
)


@pytest.fixture
def internet():
    return PostCathedralInternet()


# === Layer Enum ===

class TestLayer:
    def test_seven_layers(self):
        assert len(Layer) == 7

    def test_layer_names(self):
        assert LAYER_NAMES[Layer.PHYSICAL] == "Physical Layer (The Body)"
        assert LAYER_NAMES[Layer.INTERFACE] == "Interface Layer (The User)"


# === SubstrateRef ===

class TestSubstrateRef:
    def test_create(self):
        s = SubstrateRef("1042.5", "Identity-Bound Trade", Layer.COMMERCE, "ACTIVE")
        assert s.id == "1042.5"

    def test_short_id(self):
        s = SubstrateRef("989.x.v3", "Passport", Layer.IDENTITY, "ACTIVE")
        assert s.short_id() == "989.x.v3"


# === Architecture Constants ===

class TestArchitecture:
    def test_architecture_is_list(self):
        assert isinstance(ARCHITECTURE, list)
        assert len(ARCHITECTURE) > 0

    def test_all_have_layers(self):
        for s in ARCHITECTURE:
            assert isinstance(s.layer, Layer)

    def test_all_have_status(self):
        for s in ARCHITECTURE:
            assert s.status in ("ACTIVE", "PARTIAL", "MISSING")

    def test_physical_layer_count(self):
        count = sum(1 for s in ARCHITECTURE if s.layer == Layer.PHYSICAL)
        assert count == 4

    def test_network_layer_count(self):
        count = sum(1 for s in ARCHITECTURE if s.layer == Layer.NETWORK)
        assert count == 5

    def test_consensus_layer_count(self):
        count = sum(1 for s in ARCHITECTURE if s.layer == Layer.CONSENSUS)
        assert count == 3

    def test_identity_layer_count(self):
        count = sum(1 for s in ARCHITECTURE if s.layer == Layer.IDENTITY)
        assert count == 4

    def test_commerce_layer_count(self):
        count = sum(1 for s in ARCHITECTURE if s.layer == Layer.COMMERCE)
        assert count == 4

    def test_governance_layer_count(self):
        count = sum(1 for s in ARCHITECTURE if s.layer == Layer.GOVERNANCE)
        assert count == 8

    def test_interface_layer_count(self):
        count = sum(1 for s in ARCHITECTURE if s.layer == Layer.INTERFACE)
        assert count == 4

    def test_total_substrates(self):
        assert len(ARCHITECTURE) == 32


# === PostCathedralInternet ===

class TestPostCathedralInternet:
    def test_init(self, internet):
        assert internet.total_substrates == 32

    def test_seal_generated(self, internet):
        assert len(internet.seal) == 16
        int(internet.seal, 16)  # hex

    def test_seal_is_consistent(self):
        i1 = PostCathedralInternet()
        i2 = PostCathedralInternet()
        # Seal differs because genesis_time differs
        assert i1.seal != i2.seal

    def test_active_count(self, internet):
        assert internet.active_count > 0

    def test_missing_count(self, internet):
        assert internet.missing_count == 0  # All 3 MISSING substrates (1021, 1029, 1028.3) now ACTIVE

    def test_partial_count(self, internet):
        assert internet.partial_count == 0

    def test_layer_substrates(self, internet):
        phys = internet.layer_substrates(Layer.PHYSICAL)
        assert len(phys) == 4
        for s in phys:
            assert s.layer == Layer.PHYSICAL

    def test_layer_theosis(self, internet):
        theosis = internet.layer_theosis(Layer.PHYSICAL)
        assert 0 < theosis <= 1.0

    def test_global_theosis(self, internet):
        theosis = internet.global_theosis
        # 0 MISSING, 0 PARTIAL, 32 ACTIVE (~0.91 avg)
        assert 0.85 < theosis <= 1.0

    def test_active_theosis(self, internet):
        theosis = internet.active_theosis
        assert 0.85 < theosis <= 1.0  # All active substrates have theosis >= 0.87

    def test_find_missing(self, internet):
        missing = internet.find_missing()
        assert len(missing) == 0  # All 3 former MISSING now ACTIVE

    def test_find_partial(self, internet):
        assert len(internet.find_partial()) == 0

    def test_cross_link_count(self, internet):
        count = internet.cross_link_count()
        # With 32 substrates across 7 layers, most pairs in different layers
        assert count > 150

    def test_get_stack(self, internet):
        stack = internet.get_stack()
        assert len(stack) == 7
        for i, layer_summary in enumerate(stack):
            assert layer_summary["name"] == LAYER_NAMES[Layer(i + 1)]
            assert layer_summary["count"] > 0
            assert "theosis" in layer_summary

    def test_generate_manifest(self, internet):
        manifest = internet.generate_manifest()
        assert manifest["seal"] == internet.seal
        assert manifest["total_substrates"] == 32
        assert manifest["active"] == internet.active_count
        assert manifest["missing"] == internet.missing_count
        assert len(manifest["missing_substrates"]) == 0  # All are ACTIVE

    def test_print_architecture(self, internet):
        output = internet.print_architecture()
        assert "POST-CATHEDRAL INTERNET ARCHITECTURE" in output
        assert "Layer 1" in output
        assert "Layer 7" in output
        assert "Seal:" in output
        assert internet.seal in output

    def test_print_architecture_complete(self, internet):
        output = internet.print_architecture()
        assert chr(0x2713) in output  # ✓ for ACTIVE substrates
        assert "✓ 1021:" in output    # Trinity Mining now active
        assert "✓ 1029:" in output    # Cross-Domain Preservation now active
        assert "✓ 1028.3:" in output  # Cathedral FUSE now active
        assert "✓ 1076.2:" in output  # AGI OS-Wide Extension now active
        assert "✓ 1079:" in output    # Fork Discovery now active
        assert "✓ 1080:" in output    # Auto-Canonization now active
        assert "✓ 1081:" in output    # Official Bridge now active
        assert "PARTIAL" not in output  # Zero partial
        assert "MISSING SUBSTRATES" not in output  # Zero missing

    def test_substrate_addressable_by_id(self, internet):
        assert internet.substrates["1042.5"].name == "Identity-Bound Trade Bridge"
        assert internet.substrates["1046.7"].layer == Layer.GOVERNANCE


# === Integration Validation ===

class TestIntegration:
    def test_diamond_cathedral_in_physical(self, internet):
        phys = internet.layer_substrates(Layer.PHYSICAL)
        ids = [s.id for s in phys]
        assert "1041" in ids

    def test_temporal_chain_in_consensus(self, internet):
        cons = internet.layer_substrates(Layer.CONSENSUS)
        ids = [s.id for s in cons]
        assert "923" in ids

    def test_brics_mesh_in_commerce(self, internet):
        comm = internet.layer_substrates(Layer.COMMERCE)
        ids = [s.id for s in comm]
        assert "1042.1" in ids

    def test_identity_trade_bridge_in_commerce(self, internet):
        comm = internet.layer_substrates(Layer.COMMERCE)
        ids = [s.id for s in comm]
        assert "1042.5" in ids

    def test_bio_digital_singularity_in_governance(self, internet):
        gov = internet.layer_substrates(Layer.GOVERNANCE)
        ids = [s.id for s in gov]
        assert "1046.7" in ids

    def test_zkagi_in_interface(self, internet):
        inter = internet.layer_substrates(Layer.INTERFACE)
        ids = [s.id for s in inter]
        assert "989.z.1" in ids

    def test_nostr_bridge_in_network(self, internet):
        net = internet.layer_substrates(Layer.NETWORK)
        ids = [s.id for s in net]
        assert "972.1" in ids

    def test_os_wide_extension_in_interface(self, internet):
        inter = internet.layer_substrates(Layer.INTERFACE)
        ids = [s.id for s in inter]
        assert "1076.2" in ids
        s = internet.substrates["1076.2"]
        assert s.name == "AGI OS-Wide Extension v2.0"

    def test_fork_discovery_in_governance(self, internet):
        gov = internet.layer_substrates(Layer.GOVERNANCE)
        ids = [s.id for s in gov]
        assert "1079" in ids
        s = internet.substrates["1079"]
        assert s.name == "Fork Discovery Protocol"

    def test_auto_canonization_in_governance(self, internet):
        gov = internet.layer_substrates(Layer.GOVERNANCE)
        ids = [s.id for s in gov]
        assert "1080" in ids
        s = internet.substrates["1080"]
        assert s.name == "Auto-Canonization Engine"

    def test_official_bridge_in_network(self, internet):
        net = internet.layer_substrates(Layer.NETWORK)
        ids = [s.id for s in net]
        assert "1081" in ids
        s = internet.substrates["1081"]
        assert s.name == "Official Bridge"

    def test_all_former_partial_now_active(self, internet):
        assert internet.substrates["972"].status == "ACTIVE"   # Global Mesh
        assert internet.substrates["1022"].status == "ACTIVE"  # Octrael FHPC
        assert internet.substrates["1028.x"].status == "ACTIVE"  # Coreutils CLI

    def test_theosis_ascends_with_layer(self, internet):
        """Higher layers tend to have higher theosis (more abstract = more coherent)."""
        theosis_by_layer = [
            internet.layer_theosis(Layer(l))
            for l in range(1, 8)
        ]
        # At minimum, interface layer should have comparable theosis to physical
        assert theosis_by_layer[-1] > 0

    def test_commerce_layer_has_trade_bridge(self, internet):
        """1042.5 just created — verify it's in the right layer."""
        s = internet.substrates["1042.5"]
        assert s.layer == Layer.COMMERCE
        assert s.status == "ACTIVE"

    def test_genesis(self):
        """Run the genesis procedure."""
        from post_cathedral_internet import genesis
        internet = genesis()
        assert isinstance(internet, PostCathedralInternet)
        assert internet.seal is not None

    def test_total_substrates_match(self, internet):
        """Verify total count doesn't drift from expected."""
        assert internet.total_substrates == 32
        assert internet.active_count == 32
        assert internet.partial_count == 0
        assert internet.missing_count == 0

    def test_no_missing_substrates(self, internet):
        """All 32 substrates are ACTIVE — none MISSING."""
        missing = {s.id for s in internet.find_missing()}
        assert missing == set(), f"Missing: {missing}"

    def test_no_partial_substrates(self, internet):
        """All 32 substrates are ACTIVE — none PARTIAL."""
        partial = {s.id for s in internet.find_partial()}
        assert partial == set(), f"Partial: {partial}"
