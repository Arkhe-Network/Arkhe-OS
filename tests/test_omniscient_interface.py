"""Tests for Substrate 987 — Omniscient-Interface."""
import sys, pytest

sys.path.insert(0, "substrates/987-cathedral-omniscient-interface")
from omniscient_interface import CathedralOmniscientInterface, Query, QueryType


class TestOmniscientInterface:
    def test_classify_query_status(self):
        inte = CathedralOmniscientInterface()
        qt = inte.classify_query("Qual o estado da Catedral?")
        assert qt == QueryType.STATUS

    def test_classify_query_oracle(self):
        inte = CathedralOmniscientInterface()
        qt = inte.classify_query("Qual o preco do ETH?")
        assert qt == QueryType.ORACLE

    def test_classify_query_meta(self):
        inte = CathedralOmniscientInterface()
        qt = inte.classify_query("Quem e a Catedral?")
        assert qt == QueryType.META

    def test_classify_query_unknown(self):
        inte = CathedralOmniscientInterface()
        qt = inte.classify_query("xyzzy unknown query")
        assert qt == QueryType.META

    def test_route_query_status(self):
        inte = CathedralOmniscientInterface()
        q = Query(query_id="q1", text="status", query_type=QueryType.STATUS)
        path = inte.route_query(q)
        assert path == [983, 984, 985]

    def test_route_query_emergency(self):
        inte = CathedralOmniscientInterface()
        q = Query(query_id="q2", text="socorro", query_type=QueryType.EMERGENCY)
        path = inte.route_query(q)
        assert path == [985, 984, 979]

    def test_generate_response(self):
        inte = CathedralOmniscientInterface()
        q = Query(query_id="q3", text="Como esta a Catedral?")
        resp = inte.generate_response(q)
        assert resp.query_id == "q3"
        assert resp.response_id.startswith("resp-")
        assert len(resp.sources) > 0

    def test_generate_response_auto_classifies(self):
        inte = CathedralOmniscientInterface()
        q = Query(query_id="q4", text="Qual o preco do BTC hoje?")
        resp = inte.generate_response(q)
        assert q.query_type == QueryType.ORACLE

    def test_response_signature(self):
        inte = CathedralOmniscientInterface()
        q = Query(query_id="q5", text="status")
        resp = inte.generate_response(q)
        assert resp.orcid_signature is not None
        assert len(resp.orcid_signature) == 32

    def test_response_anchor(self):
        inte = CathedralOmniscientInterface()
        q = Query(query_id="q6", text="health?")
        resp = inte.generate_response(q)
        assert resp.temporal_anchor is not None
        assert resp.temporal_anchor.startswith("923-resp-")

    def test_generate_report(self):
        inte = CathedralOmniscientInterface()
        for t in ["status", "preco", "quem", "saude"]:
            q = Query(query_id=f"q_{t}", text=t)
            inte.generate_response(q)
        r = inte.generate_report()
        assert "Substrato 987" in r
