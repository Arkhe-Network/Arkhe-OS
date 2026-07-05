"""
Testes canônicos do Substrato 336-BIS: ORCID × Propriedade Intelectual Soberana
"""
import hashlib
import math
import pytest
from src.arkhe.l_m.orkut_2_ip_soberana import (
    ORCIDIntellectualPropertyAnchor,
    ScientistIPProfile,
    ArtistIPProfile,
    BrandIdentityRegistry,
    GHOST, LOOPSEAL, GAP_MAX,
)


# ── Fixtures ──

@pytest.fixture
def anchor():
    return ORCIDIntellectualPropertyAnchor("orcid:test-001", "Test Owner", "researcher")


@pytest.fixture
def scientist():
    return ScientistIPProfile("orcid:sci-001", "Dr. Science", "Biofotônica")


@pytest.fixture
def artist():
    return ArtistIPProfile("orcid:art-001", "Ana Criativa", "pintura digital")


@pytest.fixture
def brand_reg():
    return BrandIdentityRegistry()


# ── Test 1: ORCIDIntellectualPropertyAnchor ──

class TestORCIDAnchor:
    def test_initialization(self, anchor):
        assert anchor.orcid == "orcid:test-001"
        assert anchor.owner_name == "Test Owner"
        assert anchor.owner_type == "researcher"
        assert anchor.total_works == 0
        assert anchor.total_licenses == 0

    def test_register_work(self, anchor):
        work = anchor.register_work("paper", "Test Paper", "hash123", "2026-01-01",
                                     collaborators=["orcid:other"])
        assert work["work_type"] == "paper"
        assert work["title"] == "Test Paper"
        assert work["owner"] == "Test Owner"
        assert len(work["work_id"]) == 32
        assert hashlib.sha3_256(b"").hexdigest()[:0] == ""  # sanity
        assert anchor.total_works == 1
        assert anchor.ip_graph[work["work_id"]] == ["orcid:other"]

    def test_register_work_no_collaborators(self, anchor):
        work = anchor.register_work("artwork", "Solo Piece", "hash456", "2026-06-15")
        assert work["collaborators"] == []
        assert anchor.ip_graph[work["work_id"]] == []

    def test_issue_license(self, anchor):
        work = anchor.register_work("paper", "Licensed Work", "hash", "2026-01-01")
        lic = anchor.issue_license(work["work_id"], "orcid:licensee", "cc_by",
                                     {"exclusive": False}, 500)
        assert lic["licensor_orcid"] == "orcid:test-001"
        assert lic["licensee_orcid"] == "orcid:licensee"
        assert lic["license_type"] == "cc_by"
        assert lic["royalty_basis_points"] == 500
        assert lic["territory"] == "global"
        assert not lic["exclusive"]
        assert anchor.total_licenses == 1

    def test_issue_license_defaults(self, anchor):
        work = anchor.register_work("dataset", "Open Data", "hash", "2026-01-01")
        lic = anchor.issue_license(work["work_id"], "public", "cc0")
        assert lic["royalty_basis_points"] == 0
        assert lic["territory"] == "global"

    def test_record_revenue(self, anchor):
        work = anchor.register_work("artwork", "Valuable Art", "hash", "2026-01-01")
        rev = anchor.record_revenue(work["work_id"], 1500.0, "USD", "sale", "orcid:buyer")
        assert rev["amount"] == 1500.0
        assert rev["currency"] == "USD"
        assert rev["source"] == "sale"
        assert anchor.total_revenue == 1500.0

    def test_record_multiple_revenue(self, anchor):
        work = anchor.register_work("patent", "Patent", "hash", "2026-01-01")
        anchor.record_revenue(work["work_id"], 500, "USD", "sale")
        anchor.record_revenue(work["work_id"], 300, "USD", "royalty")
        assert anchor.total_revenue == 800.0

    def test_get_portfolio_empty(self, anchor):
        p = anchor.get_portfolio()
        assert p["total_works"] == 0
        assert p["works_by_type"] == {}
        assert p["total_collaborators"] == 0
        assert p["portfolio_phi_c"] == GHOST
        assert "canonical_seal" in p

    def test_get_portfolio_with_works(self, anchor):
        anchor.register_work("paper", "Paper 1", "h1", "2026-01-01", ["c1"])
        anchor.register_work("paper", "Paper 2", "h2", "2026-01-01", ["c1", "c2"])
        anchor.register_work("dataset", "Dataset 1", "h3", "2026-01-01")
        p = anchor.get_portfolio()
        assert p["total_works"] == 3
        assert p["works_by_type"] == {"paper": 2, "dataset": 1}
        assert p["total_collaborators"] == 2
        assert p["portfolio_phi_c"] >= GHOST

    def test_seal_consistency(self, anchor):
        work1 = anchor.register_work("paper", "Title", "h", "2026-01-01")
        work2 = anchor.register_work("paper", "Title", "h", "2026-01-01")
        assert work1["work_id"] != work2["work_id"]  # different timestamps

    def test_canonical_seal_format(self, anchor):
        p = anchor.get_portfolio()
        seal = p["canonical_seal"]
        assert len(seal) == 64  # SHA3-256 hex
        assert isinstance(seal, str)


# ── Test 2: ScientistIPProfile ──

class TestScientistIP:
    def test_initialization(self, scientist):
        assert scientist.anchor.orcid == "orcid:sci-001"
        assert scientist.field == "Biofotônica"
        assert scientist.citation_count == 0
        assert scientist.h_index == 0

    def test_publish_paper(self, scientist):
        paper = scientist.publish_paper(
            title="Quantum Coherence in Microtubules",
            abstract_hash="sha3:abc123...",
            doi="10.1234/example",
            journal="Nature",
            impact_factor=49.962,
            coauthors=["orcid:coauthor"],
            data_availability="https://example.com/data",
        )
        assert paper["work_type"] == "paper"
        assert paper["metadata"]["doi"] == "10.1234/example"
        assert paper["metadata"]["journal"] == "Nature"
        assert scientist.anchor.total_works == 1
        assert scientist.citation_count > 0

    def test_publish_multiple_papers(self, scientist):
        for i in range(3):
            scientist.publish_paper(
                title=f"Paper {i}", abstract_hash=f"hash{i}",
                doi=f"10.{i}/test", journal="Science",
            )
        assert scientist.anchor.total_works == 3
        assert scientist.h_index == int(math.sqrt(scientist.citation_count))

    def test_deposit_dataset(self, scientist):
        ds = scientist.deposit_dataset(
            title="Experimental Data", dataset_hash="ipfs:QmData...",
            size_gb=1.5, license_type="cc0",
        )
        assert ds["work_type"] == "dataset"
        assert ds["metadata"]["file_size_bytes"] == int(1.5 * 1e9)
        assert scientist.anchor.total_licenses == 1  # auto-licensed CC0

    def test_deposit_dataset_no_license(self, scientist):
        ds = scientist.deposit_dataset(
            title="Restricted Data", dataset_hash="ipfs:QmRestricted...",
            size_gb=0.5, license_type="proprietary",
        )
        assert scientist.anchor.total_licenses == 0  # no auto-license

    def test_register_patent(self, scientist):
        patent = scientist.register_patent(
            title="Bio-Photon Coherence Method",
            patent_hash="sha3:patent...",
            jurisdiction="US",
            patent_number="US20260000123",
            inventors=["orcid:sci-001", "orcid:inventor"],
        )
        assert patent["work_type"] == "patent"
        assert patent["metadata"]["patent_number"] == "US20260000123"
        assert patent["metadata"]["status"] == "pending"

    def test_get_status(self, scientist):
        scientist.publish_paper("Paper", "h", coauthors=["c1", "c2"])
        status = scientist.get_status()
        assert status["field"] == "Biofotônica"
        assert "citation_count" in status
        assert "h_index" in status
        assert "portfolio_phi_c" in status

    def test_canonical_seal(self, scientist):
        status = scientist.get_status()
        assert len(status["canonical_seal"]) == 64


# ── Test 3: ArtistIPProfile ──

class TestArtistIP:
    def test_initialization(self, artist):
        assert artist.anchor.orcid == "orcid:art-001"
        assert artist.artistic_medium == "pintura digital"
        assert len(artist.sales_history) == 0

    def test_create_artwork(self, artist):
        art = artist.create_artwork(
            title="Mona Lisa 2.0",
            artwork_hash="ipfs:QmArt...",
            dimensions={"width_cm": 100, "height_cm": 80},
            medium="pintura digital em tela",
            year=2026, edition="1/1",
        )
        assert art["work_type"] == "artwork"
        assert art["metadata"]["edition"] == "1/1"
        assert art["metadata"]["authenticity_certificate"]
        assert artist.anchor.total_works == 1

    def test_create_limited_edition(self, artist):
        art = artist.create_artwork(
            title="Edição Limitada",
            artwork_hash="ipfs:QmArt2...",
            edition="3/10",
        )
        assert art["metadata"]["edition"] == "3/10"

    def test_artwork_provenance(self, artist):
        art = artist.create_artwork("Title", "hash")
        assert artist.anchor.orcid in art["metadata"]["provenance"]

    def test_compose_music(self, artist):
        music = artist.compose_music(
            title="Symphony of Light",
            composition_hash="ipfs:QmMusic...",
            duration_seconds=300,
            genre="classical",
            instruments=["piano", "violin"],
            bpm=120,
        )
        assert music["work_type"] == "composition"
        assert music["metadata"]["duration_seconds"] == 300
        assert music["metadata"]["bpm"] == 120

    def test_compose_music_defaults(self, artist):
        music = artist.compose_music("Untitled", "hash", 180)
        assert music["metadata"]["instruments"] == []
        assert music["metadata"]["genre"] == ""

    def test_record_sale(self, artist):
        art = artist.create_artwork("Valuable Art", "hash")
        sale = artist.record_sale(art["work_id"], "orcid:buyer-001", 3.5, "ETH")
        assert sale["price"] == 3.5
        assert sale["currency"] == "ETH"
        assert len(artist.sales_history) == 1

    def test_sale_updates_revenue(self, artist):
        art = artist.create_artwork("Art", "hash")
        artist.record_sale(art["work_id"], "orcid:buyer", 2.0, "ETH")
        assert artist.anchor.total_revenue == 2.0

    def test_get_status(self, artist):
        art = artist.create_artwork("Art", "hash")
        artist.record_sale(art["work_id"], "orcid:buyer", 1.5, "ETH")
        status = artist.get_status()
        assert status["total_sales"] == 1
        assert status["total_sales_revenue"] == 1.5
        assert "portfolio_phi_c" in status

    def test_canonical_seal(self, artist):
        status = artist.get_status()
        assert len(status["canonical_seal"]) == 64


# ── Test 4: BrandIdentityRegistry ──

class TestBrandRegistry:
    def test_register_brand(self, brand_reg):
        b = brand_reg.register_brand(
            orcid="orcid:test", brand_name="Test Brand",
            logo_hash="ipfs:QmLogo...",
            color_palette=["#FF0000", "#00FF00"],
            typography={"primary": "Arial"},
            tagline="Testing",
        )
        assert b["brand_name"] == "Test Brand"
        assert b["orcid"] == "orcid:test"
        assert b["color_palette"] == ["#FF0000", "#00FF00"]
        assert "canonical_seal" in b

    def test_register_brand_defaults(self, brand_reg):
        b = brand_reg.register_brand("orcid:test2", "Minimal", "hash")
        assert b["color_palette"] == ["#000000", "#FFFFFF"]
        assert b["typography"]["primary"] == "sans-serif"

    def test_verify_ownership_true(self, brand_reg):
        brand_reg.register_brand("orcid:owner", "Brand", "ipfs:QmRealLogo")
        v = brand_reg.verify_ownership("orcid:owner", "ipfs:QmRealLogo")
        assert v["verified"]

    def test_verify_ownership_false(self, brand_reg):
        brand_reg.register_brand("orcid:owner", "Brand", "ipfs:QmRealLogo")
        v = brand_reg.verify_ownership("orcid:owner", "ipfs:QmFakeLogo")
        assert not v["verified"]

    def test_verify_nonexistent_brand(self, brand_reg):
        v = brand_reg.verify_ownership("orcid:nobody", "hash")
        assert not v["verified"]
        assert "reason" in v


# ── Test 5: Invariants ──

class TestInvariants:
    def test_ghost_value(self):
        assert GHOST == 0.577553

    def test_loopseal_value(self):
        assert abs(LOOPSEAL - math.pi / 9) < 1e-10

    def test_gap_max_value(self):
        assert GAP_MAX == 0.9999

    def test_portfolio_phi_c_respects_gap(self, anchor):
        for _ in range(20):
            anchor.register_work("paper", f"Paper {_}", f"h{_}", "2026-01-01", ["c1"])
        p = anchor.get_portfolio()
        assert p["portfolio_phi_c"] <= GAP_MAX

    def test_ghost_preserved_flag(self, anchor):
        anchor.register_work("paper", "P", "h", "2026-01-01", ["c1", "c2"])
        anchor.register_work("dataset", "D", "h2", "2026-01-01", ["c3"])
        anchor.record_revenue(anchor.works[0]["work_id"], 100, "USD", "sale")
        p = anchor.get_portfolio()
        assert p["ghost_preserved"]

    def test_ghost_preserved_with_works(self, anchor):
        anchor.register_work("paper", "P", "h", "2026-01-01", ["c1"])
        anchor.register_work("dataset", "D", "h2", "2026-01-01")
        p = anchor.get_portfolio()
        assert p["ghost_preserved"]


# ── Test 6: Edge Cases ──

class TestEdgeCases:
    def test_orcid_large_portfolio(self):
        a = ORCIDIntellectualPropertyAnchor("orcid:big", "Big", "researcher")
        for i in range(100):
            a.register_work("paper", f"Paper {i}", f"hash{i}", "2026-01-01")
        p = a.get_portfolio()
        assert p["total_works"] == 100
        assert p["portfolio_phi_c"] <= GAP_MAX

    def test_mixed_owner_types(self):
        a1 = ORCIDIntellectualPropertyAnchor("o1", "Name1", "researcher")
        a2 = ORCIDIntellectualPropertyAnchor("o2", "Name2", "artist")
        assert a1.owner_type == "researcher"
        assert a2.owner_type == "artist"

    def test_license_has_seal(self, anchor):
        w = anchor.register_work("paper", "T", "h", "2026-01-01")
        lic = anchor.issue_license(w["work_id"], "lic", "cc_by")
        assert len(lic["canonical_seal"]) == 64

    def test_revenue_has_seal(self, anchor):
        w = anchor.register_work("paper", "T", "h", "2026-01-01")
        rev = anchor.record_revenue(w["work_id"], 100, "USD", "sale")
        assert len(rev["canonical_seal"]) == 64

    def test_seal_uniqueness(self, anchor):
        s1 = anchor.register_work("paper", "T1", "h1", "2026-01-01")["canonical_seal"]
        s2 = anchor.register_work("paper", "T2", "h2", "2026-01-01")["canonical_seal"]
        assert s1 != s2
