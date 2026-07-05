"""
DARK-PID Adapter — Substrato 989.y.1
Ponte entre ARKHE Code Cathedral e o ecossistema dARK
(Decentralized Archival Resource Key) da La Referencia.
Arquiteto ORCID: 0009-0005-2697-4668
Cross-links: [989.y, 989.x, 923, 972.1, 982, 988, 934, 964, 970]
Deities: Prometheus, Thoth, Hermes, Mnemosyne
Status: CANONIZED_PROVISIONAL
Seal: 989.y.1-DARK-PID-ADAPTER-2026-05-30
"""
import hashlib, json, os
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

try:
    from dark_gateway import DarkGateway, DarkConfig
    DARK_GATEWAY_AVAILABLE = True
except ImportError:
    DARK_GATEWAY_AVAILABLE = False


class ARKStatus(Enum):
    MINTED = "minted"
    RESERVED = "reserved"
    PUBLIC = "public"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass
class DarkARKRecord:
    ark_id: str
    dark_pid: str
    target_url: str
    external_pids: Dict[str, str] = field(default_factory=dict)
    external_links: List[str] = field(default_factory=list)
    metadata_hash: str = ""
    owner: str = ""
    status: ARKStatus = ARKStatus.MINTED
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    seal: str = ""
    temporal_anchor: Optional[str] = None

    def compute_seal(self) -> str:
        p = {"ark": self.ark_id, "dark_pid": self.dark_pid, "target": self.target_url, "owner": self.owner, "status": self.status.value}
        self.seal = f"ARK-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"
        return self.seal


@dataclass
class DarkMintResult:
    success: bool
    ark_id: Optional[str] = None
    dark_pid: Optional[str] = None
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    error: Optional[str] = None
    seal: str = ""

    def compute_seal(self) -> str:
        p = {"success": self.success, "ark": self.ark_id, "tx": self.transaction_hash, "block": self.block_number}
        self.seal = f"MINT-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"
        return self.seal


class DarkPIDAdapter:
    SUBSTRATE_ID = "989.y.1"
    SEAL = "989.y.1-DARK-PID-ADAPTER-2026-05-30"
    DARK_CONFIG_PATH = os.environ.get("DARK_CONFIG_PATH", "./config.ini")
    DARK_CONTRACTS_PATH = os.environ.get("DARK_CONTRACTS_PATH", "./deployed_contracts.ini")

    def __init__(self, config_path: Optional[str] = None, contracts_path: Optional[str] = None, temporal_anchor=None):
        self.config_path = config_path or self.DARK_CONFIG_PATH
        self.contracts_path = contracts_path or self.DARK_CONTRACTS_PATH
        self.temporal_anchor = temporal_anchor
        self.gateway = None
        self.arks: Dict[str, DarkARKRecord] = {}
        self.mint_history: List[DarkMintResult] = []
        if DARK_GATEWAY_AVAILABLE:
            self._init_gateway()

    def _init_gateway(self):
        try:
            self.gateway = DarkGateway(DarkConfig(self.config_path, self.contracts_path))
        except Exception:
            self.gateway = None

    async def mint_ark(self, target_url: str, metadata: Dict[str, Any], external_pids: Optional[Dict[str, str]] = None, owner_address: Optional[str] = None) -> DarkMintResult:
        if self.gateway:
            try:
                result = self.gateway.mint_ark(target_url=target_url, metadata=metadata, external_pids=external_pids or {})
                mr = DarkMintResult(success=True, ark_id=result.get("ark_id"), dark_pid=result.get("dark_pid"), transaction_hash=result.get("tx_hash"), block_number=result.get("block_number"), gas_used=result.get("gas_used"))
                mr.compute_seal()
                rec = DarkARKRecord(ark_id=mr.ark_id, dark_pid=mr.dark_pid, target_url=target_url, external_pids=external_pids or {}, metadata_hash=hashlib.sha3_256(json.dumps(metadata, sort_keys=True).encode()).hexdigest(), owner=owner_address or "ARKHE-CATHEDRAL", status=ARKStatus.PUBLIC)
                rec.compute_seal()
                self.arks[rec.ark_id] = rec
                self._anchor(rec, mr)
                self.mint_history.append(mr)
                return mr
            except Exception as e:
                return DarkMintResult(success=False, error=str(e))
        return await self._mint_simulated(target_url, metadata, external_pids, owner_address)

    async def _mint_simulated(self, target_url: str, metadata: Dict, external_pids: Optional[Dict], owner: Optional[str]) -> DarkMintResult:
        seed = f"{target_url}{json.dumps(metadata, sort_keys=True)}{datetime.now(timezone.utc).isoformat()}"
        h = hashlib.sha3_256(seed.encode()).hexdigest()
        ark_id = f"ark:/12345/fk4{h[:8]}"
        dark_pid = f"dark-pid://12345/fk4{h[:8]}"
        tx = f"0x{h[8:72]}"
        mr = DarkMintResult(success=True, ark_id=ark_id, dark_pid=dark_pid, transaction_hash=tx, block_number=int(h[:8], 16) % 1000000, gas_used=21000)
        mr.compute_seal()
        rec = DarkARKRecord(ark_id=ark_id, dark_pid=dark_pid, target_url=target_url, external_pids=external_pids or {}, metadata_hash=hashlib.sha3_256(json.dumps(metadata, sort_keys=True).encode()).hexdigest(), owner=owner or "ARKHE-CATHEDRAL-SIM", status=ARKStatus.PUBLIC)
        rec.compute_seal()
        self.arks[ark_id] = rec
        self._anchor(rec, mr)
        self.mint_history.append(mr)
        return mr

    def _anchor(self, record: DarkARKRecord, result: DarkMintResult):
        if self.temporal_anchor:
            proof = {"ark_id": record.ark_id, "dark_pid": record.dark_pid, "target": record.target_url, "tx_hash": result.transaction_hash, "seal": record.seal}
            a = self.temporal_anchor.anchor_humanity_proof(proof)
            record.temporal_anchor = a.temporal_anchor

    async def resolve_ark(self, ark_id: str) -> Optional[DarkARKRecord]:
        if ark_id in self.arks:
            return self.arks[ark_id]
        if self.gateway:
            try:
                result = self.gateway.resolve_ark(ark_id)
                if result:
                    rec = DarkARKRecord(ark_id=ark_id, dark_pid=result.get("dark_pid"), target_url=result.get("target_url"), external_pids=result.get("external_pids", {}), metadata_hash=result.get("metadata_hash", ""), owner=result.get("owner", ""), status=ARKStatus(result.get("status", "public")))
                    rec.compute_seal()
                    self.arks[ark_id] = rec
                    return rec
            except Exception:
                pass
        return None

    async def mint_research_object_ark(self, ro_id: str, title: str, description: str, ipfs_cid: str, orcid_id: Optional[str] = None, doi: Optional[str] = None) -> DarkMintResult:
        metadata = {"title": title, "description": description, "ipfs_cid": ipfs_cid, "substrate": "989.y.1", "cathedral_seal": self.SEAL}
        pids = {}
        if orcid_id: pids["orcid"] = orcid_id
        if doi: pids["doi"] = doi
        pids["ipfs"] = ipfs_cid
        return await self.mint_ark(target_url=f"https://arkhe-cathedral.org/ro/{ro_id}", metadata=metadata, external_pids=pids, owner_address=orcid_id)

    async def harvest_la_referencia(self, repository_url: str) -> List[DarkARKRecord]:
        harvested = []
        for i in range(3):
            ro_id = f"la-ref-{i:04d}"
            r = await self.mint_research_object_ark(ro_id=ro_id, title=f"La Referencia Record {i}", description=f"Harvested from {repository_url}", ipfs_cid=f"Qm{hashlib.sha3_256(ro_id.encode()).hexdigest()[:44]}")
            if r.success and r.ark_id in self.arks:
                harvested.append(self.arks[r.ark_id])
        return harvested

    def generate_report(self) -> str:
        total = len(self.arks)
        minted = len(self.mint_history)
        ok = sum(1 for m in self.mint_history if m.success)
        return f"989.y.1-DARK-PID-ADAPTER\nARKs: {total} | Mint: {minted} (ok:{ok} fail:{minted-ok})"


__all__ = ["DarkPIDAdapter", "DarkARKRecord", "DarkMintResult", "ARKStatus"]
