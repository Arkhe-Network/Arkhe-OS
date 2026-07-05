"""
DeSci Nodes Bridge — Substrato 989.y
Ponte entre DeSci Labs (FAIR research objects, IPFS, dPID) e ARKHE Code Cathedral.
Deities: Prometheus, Athena, Mnemosyne, Thoth
"""
import hashlib, json
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class ResearchObjectType(Enum):
    PUBLICATION = "publication"
    DATASET = "dataset"
    CODE = "code"
    PROTOCOL = "protocol"
    MODEL = "model"
    HYPOTHESIS = "hypothesis"
    REVIEW = "review"


@dataclass
class FAIRMetadata:
    dpid: str
    doi: Optional[str] = None
    orcid_id: Optional[str] = None
    title: str = ""
    description: str = ""
    keywords: list = field(default_factory=list)
    access_protocol: str = "https"
    access_level: str = "public"
    license: str = "CC-BY-4.0"
    data_format: str = "json"
    ontology: str = "schema.org"
    cross_references: list = field(default_factory=list)
    provenance: str = ""
    version: str = "1.0.0"
    creation_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def compute_fair_score(self) -> float:
        s = 0.0
        if self.dpid: s += 0.0625
        if self.doi: s += 0.0625
        if self.title and self.description: s += 0.0625
        if self.keywords: s += 0.0625
        if self.access_protocol: s += 0.125
        if self.license: s += 0.125
        if self.data_format: s += 0.125
        if self.ontology: s += 0.125
        if self.provenance: s += 0.125
        if self.version: s += 0.125
        return s


@dataclass
class ResearchObject:
    ro_id: str
    ro_type: ResearchObjectType
    cid: str
    manifest_cid: str
    content_hash: str
    fair: FAIRMetadata
    cathedral_substrates: list = field(default_factory=list)
    cathedral_seals: list = field(default_factory=list)
    is_published: bool = False
    is_peer_reviewed: bool = False
    review_count: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    temporal_anchor: Optional[str] = None
    seal: str = ""

    def compute_seal(self) -> str:
        p = {"ro_id": self.ro_id, "cid": self.cid, "type": self.ro_type.value, "fair_score": round(self.fair.compute_fair_score(), 4), "timestamp": self.timestamp}
        self.seal = f"RO-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"
        return self.seal


class DeSciNodesBridge:
    SUBSTRATE_ID = "989.y"
    SEAL = "989.y-DESCI-NODES-BRIDGE-A1B2C3D4E5F67890"

    def __init__(self):
        self.research_objects = {}
        self.dpid_counter = 1000

    def generate_dpid(self) -> str:
        self.dpid_counter += 1
        return f"dpid-{self.dpid_counter:06d}-arkhe"

    async def create_research_object(self, ro_type: ResearchObjectType, content: bytes, title: str, description: str, orcid_id: Optional[str] = None, keywords: list = None, cathedral_substrates: list = None) -> ResearchObject:
        dpid = self.generate_dpid()
        content_hash = hashlib.sha3_256(content).hexdigest()
        cid = f"Qm{hashlib.sha3_256(content).hexdigest()[:44]}"
        manifest = {"dpid": dpid, "type": ro_type.value, "title": title, "content_hash": content_hash, "cid": cid, "timestamp": datetime.now(timezone.utc).isoformat(), "substrate": self.SUBSTRATE_ID}
        manifest_cid = f"Qm{hashlib.sha3_256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:44]}"
        fair = FAIRMetadata(dpid=dpid, orcid_id=orcid_id, title=title, description=description, keywords=keywords or [], provenance=f"Created via ARKHE DeSci Bridge {self.SUBSTRATE_ID}")
        ro = ResearchObject(ro_id=dpid, ro_type=ro_type, cid=cid, manifest_cid=manifest_cid, content_hash=content_hash, fair=fair, cathedral_substrates=cathedral_substrates or [], cathedral_seals=[self.SEAL])
        ro.compute_seal()
        self.research_objects[dpid] = ro
        return ro

    def link_to_substrate(self, dpid: str, substrate_id: int, substrate_seal: str) -> bool:
        if dpid not in self.research_objects:
            return False
        ro = self.research_objects[dpid]
        if substrate_id not in ro.cathedral_substrates:
            ro.cathedral_substrates.append(substrate_id)
        if substrate_seal not in ro.cathedral_seals:
            ro.cathedral_seals.append(substrate_seal)
        return True

    def get_fair_report(self, dpid: str) -> Optional[Dict[str, Any]]:
        if dpid not in self.research_objects:
            return None
        ro = self.research_objects[dpid]
        return {"dpid": dpid, "type": ro.ro_type.value, "fair_score": ro.fair.compute_fair_score(), "findable": {"dpid": ro.fair.dpid, "doi": ro.fair.doi, "title": ro.fair.title, "keywords": ro.fair.keywords}, "accessible": {"protocol": ro.fair.access_protocol, "license": ro.fair.license}, "interoperable": {"format": ro.fair.data_format}, "reusable": {"provenance": ro.fair.provenance, "version": ro.fair.version}, "cathedral_links": {"substrates": ro.cathedral_substrates, "seals": ro.cathedral_seals}, "seal": ro.seal, "temporal_anchor": ro.temporal_anchor}

    def generate_report(self) -> str:
        total = len(self.research_objects)
        avg_fair = sum(ro.fair.compute_fair_score() for ro in self.research_objects.values()) / total if total > 0 else 0
        return f"989.y-DESCI-NODES-BRIDGE\nTotal: {total}\nAvg FAIR: {avg_fair:.2%}"


__all__ = ["DeSciNodesBridge", "ResearchObject", "ResearchObjectType", "FAIRMetadata"]
