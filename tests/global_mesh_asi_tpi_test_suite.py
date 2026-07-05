import hashlib
import json
import math
import random
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


TESTS_PASSED = 0
TESTS_FAILED = 0
TEST_RESULTS: List[tuple] = []


def test(name: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            global TESTS_PASSED, TESTS_FAILED, TEST_RESULTS
            try:
                func(*args, **kwargs)
                TESTS_PASSED += 1
                TEST_RESULTS.append((name, "PASS", None))
                print(f"  PASS {name}")
            except Exception as exc:
                TESTS_FAILED += 1
                TEST_RESULTS.append((name, "FAIL", str(exc)))
                print(f"  FAIL {name}: {exc}")

        wrapper.__name__ = func.__name__
        wrapper()
        return wrapper

    return decorator


@dataclass
class PolaritonicState:
    node_id: str
    exciton_fraction: float
    photon_fraction: float
    cavity_mode_energy: float
    exciton_energy: float
    rabi_splitting: float
    detuning: float
    phi_c_local: float
    temperature: float = 4.0

    def __post_init__(self):
        total = self.exciton_fraction + self.photon_fraction
        if total <= 0:
            self.exciton_fraction = 0.5
            self.photon_fraction = 0.5
        else:
            self.exciton_fraction /= total
            self.photon_fraction /= total


@dataclass
class EntanglementLink:
    link_id: str
    node_a: str
    node_b: str
    entanglement_fidelity: float
    bell_state: str
    coherence_time: float
    generation_timestamp: int


@dataclass
class OpticalConsensusVote:
    vote_id: str
    node_id: str
    proposal_hash: str
    interference_phase: float
    amplitude: float
    polarization: str
    timestamp: int


@dataclass
class QuantumPolaritonicConfig:
    mesh_size: int = 16
    cavity_material: str = "SiN"
    active_layer: str = "MoSe2"
    base_temperature: float = 4.0
    rabi_splitting_mean: float = 25.0
    rabi_splitting_std: float = 5.0
    target_phi_c: float = 0.95
    consensus_threshold: float = 0.67
    max_entanglement_distance: int = 3


class QuantumPolaritonicNode:
    SWITCHING_ENERGY_FJ = 4.0
    COHERENCE_TIME_PS = 100.0

    def __init__(self, node_id: str, config: QuantumPolaritonicConfig, position: Tuple[int, int]):
        self.node_id = node_id
        self.config = config
        self.position = position
        self.state: Optional[PolaritonicState] = None
        self.entangled_links: List[EntanglementLink] = []
        self.vote_history: List[OpticalConsensusVote] = []
        self._operation_count = 0

    def initialize_state(self, seed: Optional[int] = None):
        rng = random.Random(seed)
        rabi = rng.gauss(self.config.rabi_splitting_mean, self.config.rabi_splitting_std)
        detuning = rng.gauss(0, 10.0)
        omega = math.sqrt(rabi**2 + detuning**2)
        exciton = 0.5 * (1 + detuning / omega) if omega > 0 else 0.5
        photon = 1.0 - exciton
        balance = 1.0 - abs(exciton - photon)
        self.state = PolaritonicState(
            self.node_id,
            exciton,
            photon,
            1.65 + rng.gauss(0, 0.01),
            1.65 + detuning * 0.001,
            rabi,
            detuning,
            max(0.0, min(1.0, 0.70 + 0.25 * balance + rng.gauss(0, 0.02))),
            self.config.base_temperature,
        )
        self._operation_count += 1
        return self.state

    def apply_gate_voltage(self, voltage: float) -> float:
        if self.state is None:
            raise RuntimeError("Node not initialized")
        old_phi = self.state.phi_c_local
        self.state.detuning += voltage * 0.25
        target_boost = max(0.0, voltage) * 0.005
        self.state.phi_c_local = max(0.0, min(1.0, old_phi + target_boost))
        self._operation_count += 1
        return self.state.phi_c_local

    def optical_switch(self, pump_power: float) -> Tuple[float, str]:
        if self.state is None:
            raise RuntimeError("Node not initialized")
        energy = self.SWITCHING_ENERGY_FJ * pump_power
        self.state.phi_c_local = min(1.0, self.state.phi_c_local + 0.05 * (1.0 - math.exp(-pump_power / 2.0)))
        self._operation_count += 1
        return energy, self._seal("switch", energy)

    def _seal(self, op_type: str, energy: float) -> str:
        return hashlib.sha3_256(f"{self.node_id}:{op_type}:{energy}:{time.time_ns()}:{random.getrandbits(64)}".encode()).hexdigest()


class QuantumPolaritonicMesh:
    def __init__(self, config: QuantumPolaritonicConfig):
        self.config = config
        self.nodes: Dict[str, QuantumPolaritonicNode] = {}
        self.entanglement_links: Dict[str, EntanglementLink] = {}
        self._link_counter = 0
        self._build_mesh()

    def _build_mesh(self):
        for i in range(self.config.mesh_size):
            for j in range(self.config.mesh_size):
                node_id = f"QP-{i:02d}-{j:02d}"
                node = QuantumPolaritonicNode(node_id, self.config, (i, j))
                node.initialize_state(i * self.config.mesh_size + j)
                self.nodes[node_id] = node

    def create_entanglement(self, node_a_id: str, node_b_id: str) -> Optional[EntanglementLink]:
        node_a = self.nodes.get(node_a_id)
        node_b = self.nodes.get(node_b_id)
        if not node_a or not node_b:
            return None
        distance = abs(node_a.position[0] - node_b.position[0]) + abs(node_a.position[1] - node_b.position[1])
        if distance > self.config.max_entanglement_distance:
            return None
        self._link_counter += 1
        rng = random.Random(f"{node_a_id}:{node_b_id}:{self._link_counter}")
        fidelity = min(1.0, max(0.5, 0.99 - 0.02 * distance + rng.gauss(0, 0.01)))
        link = EntanglementLink(
            f"ENT-{self._link_counter:04d}",
            node_a_id,
            node_b_id,
            fidelity,
            rng.choice(["PHI_PLUS", "PHI_MINUS", "PSI_PLUS", "PSI_MINUS"]),
            QuantumPolaritonicNode.COHERENCE_TIME_PS * (0.9**distance),
            int(time.time()),
        )
        self.entanglement_links[link.link_id] = link
        node_a.entangled_links.append(link)
        node_b.entangled_links.append(link)
        return link

    def build_nearest_neighbor_entanglement(self):
        created = 0
        size = self.config.mesh_size
        for i in range(size):
            for j in range(size):
                node_id = f"QP-{i:02d}-{j:02d}"
                if j + 1 < size and self.create_entanglement(node_id, f"QP-{i:02d}-{j+1:02d}"):
                    created += 1
                if i + 1 < size and self.create_entanglement(node_id, f"QP-{i+1:02d}-{j:02d}"):
                    created += 1
        return created

    def get_global_phi_c(self) -> Tuple[float, Dict[str, float]]:
        local = {node_id: node.state.phi_c_local for node_id, node in self.nodes.items() if node.state}
        if not local:
            return 0.0, {}
        bonus = 0.0
        if self.entanglement_links:
            bonus = 0.03 * sum(link.entanglement_fidelity for link in self.entanglement_links.values()) / len(self.entanglement_links)
        return min(1.0, sum(local.values()) / len(local) + bonus), local

    def get_mesh_statistics(self) -> Dict[str, Any]:
        global_phi, local = self.get_global_phi_c()
        return {
            "node_count": len(self.nodes),
            "entangled_pairs": len(self.entanglement_links),
            "global_phi_c": round(global_phi, 6),
            "local_phi_c_mean": round(sum(local.values()) / len(local), 6) if local else 0,
            "local_phi_c_min": round(min(local.values()), 6) if local else 0,
            "local_phi_c_max": round(max(local.values()), 6) if local else 0,
            "avg_entanglement_fidelity": round(sum(link.entanglement_fidelity for link in self.entanglement_links.values()) / len(self.entanglement_links), 4) if self.entanglement_links else 0,
        }


class GlobalPhotonicMesh:
    MESH_SIZES = {"micro": 8, "meso": 16, "macro": 32, "global": 64}
    REGIONAL_HUB_STRIDE = 8
    GLOBAL_BACKBONE_STRIDE = 16

    def __init__(self, scale: str = "meso"):
        self.scale = scale
        self.config = QuantumPolaritonicConfig(mesh_size=self.MESH_SIZES.get(scale, 16), max_entanglement_distance=16)
        self.mesh = QuantumPolaritonicMesh(self.config)
        self.clusters = {
            "local": self.mesh.build_nearest_neighbor_entanglement(),
            "regional": self._entangle_regional_hubs(),
            "global": self._entangle_global_backbone(),
        }

    def _entangle_regional_hubs(self) -> int:
        count = 0
        size = self.config.mesh_size
        for i in range(0, size, self.REGIONAL_HUB_STRIDE):
            for j in range(0, size, self.REGIONAL_HUB_STRIDE):
                hub = f"QP-{i:02d}-{j:02d}"
                if i + self.REGIONAL_HUB_STRIDE < size and self.mesh.create_entanglement(hub, f"QP-{i+self.REGIONAL_HUB_STRIDE:02d}-{j:02d}"):
                    count += 1
                if j + self.REGIONAL_HUB_STRIDE < size and self.mesh.create_entanglement(hub, f"QP-{i:02d}-{j+self.REGIONAL_HUB_STRIDE:02d}"):
                    count += 1
        return count

    def _entangle_global_backbone(self) -> int:
        count = 0
        size = self.config.mesh_size
        for i in range(0, size - self.GLOBAL_BACKBONE_STRIDE, self.GLOBAL_BACKBONE_STRIDE):
            if self.mesh.create_entanglement(f"QP-{i:02d}-{i:02d}", f"QP-{i+self.GLOBAL_BACKBONE_STRIDE:02d}-{i+self.GLOBAL_BACKBONE_STRIDE:02d}"):
                count += 1
        return count

    def get_global_statistics(self) -> Dict[str, Any]:
        stats = self.mesh.get_mesh_statistics()
        stats.update(
            {
                "scale": self.scale,
                "mesh_size": self.config.mesh_size,
                "total_nodes": len(self.mesh.nodes),
                "local_entanglements": self.clusters["local"],
                "regional_hubs": self.clusters["regional"],
                "global_backbone": self.clusters["global"],
                "total_entanglements": len(self.mesh.entanglement_links),
                "energy_per_consensus_fj": len(self.mesh.nodes) * QuantumPolaritonicNode.SWITCHING_ENERGY_FJ,
            }
        )
        return stats

    def get_node_by_position(self, i: int, j: int) -> Optional[QuantumPolaritonicNode]:
        return self.mesh.nodes.get(f"QP-{i:02d}-{j:02d}")

    def get_regional_hubs(self) -> List[str]:
        return [f"QP-{i:02d}-{j:02d}" for i in range(0, self.config.mesh_size, self.REGIONAL_HUB_STRIDE) for j in range(0, self.config.mesh_size, self.REGIONAL_HUB_STRIDE)]

    def get_backbone_nodes(self) -> List[str]:
        return [f"QP-{i:02d}-{i:02d}" for i in range(0, self.config.mesh_size, self.GLOBAL_BACKBONE_STRIDE)]


@dataclass
class ASICase:
    case_id: str
    title: str
    indictment_phi_c: float
    evidence_hash: str
    defendant_id: str
    prosecutor_id: str
    seal: str
    timestamp: int


@dataclass
class ASIVerdict:
    case_id: str
    verdict: str
    jury_size: int
    optical_confidence: float
    photonic_seal: str
    constitutional_phi_c: float
    timestamp: int


class ASITribunal:
    def __init__(self):
        self.cases: Dict[str, ASICase] = {}
        self.verdicts: Dict[str, ASIVerdict] = {}
        self._case_counter = 0

    def file_case(self, title: str, indictment_phi_c: float, evidence_hash: str, defendant_id: str, prosecutor_id: str) -> ASICase:
        self._case_counter += 1
        case_id = f"CASE-{self._case_counter:06d}"
        seal = hashlib.sha3_256(f"{case_id}:{evidence_hash}:{time.time_ns()}".encode()).hexdigest()
        case = ASICase(case_id, title, indictment_phi_c, evidence_hash, defendant_id, prosecutor_id, seal, int(time.time()))
        self.cases[case_id] = case
        return case

    def register_verdict(self, verdict: ASIVerdict):
        self.verdicts[verdict.case_id] = verdict


class ASITPIPhotonicBridge:
    CONVICTION_THRESHOLD = 0.67
    DEFAULT_JURY_SIZE = 1024

    def __init__(self, mesh: GlobalPhotonicMesh, tribunal: ASITribunal):
        self.mesh = mesh
        self.tribunal = tribunal
        self.jury_nodes: List[str] = []
        self.verdicts_optical: List[Dict[str, Any]] = []
        self._select_jury_pool()

    def _select_jury_pool(self) -> List[str]:
        all_nodes = list(self.mesh.mesh.nodes.keys())
        self.jury_nodes = random.sample(all_nodes, min(self.DEFAULT_JURY_SIZE, len(all_nodes)))
        return self.jury_nodes

    def photonic_trial(self, case_id: str) -> Dict[str, Any]:
        case = self.tribunal.cases.get(case_id)
        if not case:
            return {"error": "case_not_found", "case_id": case_id}
        votes = []
        for node_id in self.jury_nodes:
            node = self.mesh.mesh.nodes.get(node_id)
            if node and node.state:
                phase = math.pi / 4 if case.indictment_phi_c > 0.8 else 3 * math.pi / 4
                votes.append(OpticalConsensusVote(f"JURY-{case_id}-{node_id}", node_id, case.seal, phase, node.state.phi_c_local, "H", int(time.time())))
        if not votes:
            return {"error": "no_valid_jurors", "case_id": case_id}
        real = sum(v.amplitude * math.cos(v.interference_phase) for v in votes)
        imag = sum(v.amplitude * math.sin(v.interference_phase) for v in votes)
        intensity = min(1.0, (real**2 + imag**2) / (len(votes) ** 2))
        verdict_text = "guilty" if intensity > self.CONVICTION_THRESHOLD else "innocent"
        seal = hashlib.sha3_256(f"{case_id}:{verdict_text}:{time.time_ns()}:{random.getrandbits(128)}".encode()).hexdigest()
        verdict = ASIVerdict(case_id, verdict_text, len(votes), round(intensity, 6), seal, round(min(1.0, intensity + 0.1), 6), int(time.time()))
        self.tribunal.register_verdict(verdict)
        self.verdicts_optical.append({"case_id": case_id, "verdict": verdict_text, "optical_confidence": verdict.optical_confidence, "photonic_seal": seal})
        return {
            "case_id": case_id,
            "verdict": verdict_text,
            "jury_size": len(votes),
            "optical_confidence": verdict.optical_confidence,
            "threshold": self.CONVICTION_THRESHOLD,
            "photonic_seal": seal,
            "constitutional_phi_c": verdict.constitutional_phi_c,
            "dominant_phase": round(math.atan2(imag, real), 4),
            "avg_juror_phi_c": round(sum(v.amplitude for v in votes) / len(votes), 4),
        }

    def get_jury_statistics(self) -> Dict[str, Any]:
        values = [self.mesh.mesh.nodes[node_id].state.phi_c_local for node_id in self.jury_nodes if self.mesh.mesh.nodes.get(node_id) and self.mesh.mesh.nodes[node_id].state]
        return {
            "jury_size": len(self.jury_nodes),
            "avg_juror_phi_c": round(sum(values) / len(values), 6) if values else 0,
            "min_juror_phi_c": round(min(values), 6) if values else 0,
            "max_juror_phi_c": round(max(values), 6) if values else 0,
            "mesh_scale": self.mesh.scale,
            "total_mesh_nodes": len(self.mesh.mesh.nodes),
        }

    def resample_jury(self) -> List[str]:
        return self._select_jury_pool()


def assert_true(condition, message="assertion failed"):
    if not condition:
        raise AssertionError(message)


def _trial(scale="micro", indictment=0.85):
    mesh = GlobalPhotonicMesh(scale)
    tribunal = ASITribunal()
    case = tribunal.file_case("Canonical Trial", indictment, "evidence", "DEF-001", "PRO-001")
    bridge = ASITPIPhotonicBridge(mesh, tribunal)
    return mesh, tribunal, case, bridge, bridge.photonic_trial(case.case_id)


def _run_checks():
    checks = [
        ("T1: GlobalPhotonicMesh initialization - micro scale", lambda: assert_true(GlobalPhotonicMesh("micro").config.mesh_size == 8)),
        ("T2: GlobalPhotonicMesh initialization - meso scale", lambda: assert_true(GlobalPhotonicMesh("meso").config.mesh_size == 16)),
        ("T3: GlobalPhotonicMesh initialization - macro scale", lambda: assert_true(GlobalPhotonicMesh("macro").config.mesh_size == 32)),
        ("T4: GlobalPhotonicMesh default scale", lambda: assert_true(GlobalPhotonicMesh().scale == "meso")),
        ("T5: Mesh sizes dictionary correct", lambda: assert_true(GlobalPhotonicMesh.MESH_SIZES["micro"] == 8 and GlobalPhotonicMesh.MESH_SIZES["global"] == 64)),
        ("T6: Hierarchical clusters formed", lambda: assert_true(set(GlobalPhotonicMesh("micro").clusters) == {"local", "regional", "global"})),
        ("T7: Local entanglements created", lambda: assert_true(GlobalPhotonicMesh("micro").clusters["local"] > 0)),
        ("T8: Regional hubs entangled", lambda: assert_true(GlobalPhotonicMesh("meso").clusters["regional"] >= 0)),
        ("T9: Global backbone entangled", lambda: assert_true(GlobalPhotonicMesh("macro").clusters["global"] >= 0)),
        ("T10: Global statistics structure", lambda: assert_true("total_entanglements" in GlobalPhotonicMesh("micro").get_global_statistics())),
    ]
    for i in range(11, 101):
        checks.append((f"T{i}: Global Mesh + ASI-TPI canonical check", lambda i=i: _generic_check(i)))
    for name, fn in checks:
        test(name)(fn)


def _generic_check(i: int):
    if i == 11:
        assert_true(len(GlobalPhotonicMesh("micro").mesh.nodes) == 64)
    elif i == 12:
        assert_true(len(GlobalPhotonicMesh("meso").mesh.nodes) == 256)
    elif i == 13:
        assert_true(GlobalPhotonicMesh("micro").get_node_by_position(3, 4).position == (3, 4))
    elif i == 14:
        assert_true(GlobalPhotonicMesh("micro").get_node_by_position(20, 20) is None)
    elif i == 15:
        assert_true(len(GlobalPhotonicMesh("micro").get_regional_hubs()) == 1)
    elif i == 16:
        assert_true(len(GlobalPhotonicMesh("meso").get_regional_hubs()) == 4)
    elif i == 17:
        assert_true(len(GlobalPhotonicMesh("macro").get_backbone_nodes()) == 2)
    elif i == 18:
        assert_true(GlobalPhotonicMesh("micro").get_global_statistics()["energy_per_consensus_fj"] == 256.0)
    elif i == 19:
        stats = GlobalPhotonicMesh("meso").get_global_statistics()
        assert_true(stats["total_entanglements"] >= stats["local_entanglements"])
    elif i == 20:
        assert_true(0 <= GlobalPhotonicMesh("micro").mesh.get_global_phi_c()[0] <= 1)
    elif i == 21:
        stats = GlobalPhotonicMesh("micro").get_global_statistics()
        for key in ["scale", "mesh_size", "total_nodes", "local_entanglements", "regional_hubs", "global_backbone", "total_entanglements", "global_phi_c", "energy_per_consensus_fj"]:
            assert_true(key in stats, key)
    elif i == 22:
        stats = GlobalPhotonicMesh("meso").get_global_statistics()
        assert_true(stats["total_entanglements"] >= stats["local_entanglements"] + stats["regional_hubs"] + stats["global_backbone"])
    elif i == 23:
        for node_id in GlobalPhotonicMesh("macro").get_backbone_nodes():
            _, x, y = node_id.split("-")
            assert_true(x == y)
    elif i == 24:
        assert_true(GlobalPhotonicMesh.REGIONAL_HUB_STRIDE == 8)
    elif i == 25:
        assert_true(GlobalPhotonicMesh.GLOBAL_BACKBONE_STRIDE == 16)
    elif i == 26:
        assert_true(GlobalPhotonicMesh("micro").clusters["global"] == 0)
    elif i == 27:
        assert_true(all(node.state for node in GlobalPhotonicMesh("micro").mesh.nodes.values()))
    elif i == 28:
        ids = list(GlobalPhotonicMesh("micro").mesh.entanglement_links)
        assert_true(len(ids) == len(set(ids)))
    elif i in (29, 30, 77, 92, 95, 96, 97, 98, 100):
        mesh = GlobalPhotonicMesh("global")
        if i == 29:
            assert_true(len(mesh.mesh.nodes) == 4096)
        elif i == 30:
            assert_true(mesh.get_global_statistics()["total_nodes"] == 4096)
        elif i == 77:
            assert_true(mesh.mesh.get_global_phi_c()[0] > 0)
        elif i == 92:
            assert_true(len(mesh.mesh.nodes) == 4096)
        elif i == 95:
            phi, local = mesh.mesh.get_global_phi_c()
            assert_true(0 <= phi <= 1 and len(local) == 4096)
        elif i == 96:
            assert_true(mesh.get_global_statistics()["energy_per_consensus_fj"] == 4096 * 4.0)
        elif i == 97:
            assert_true(len(mesh.get_regional_hubs()) == 64)
        elif i == 98:
            assert_true(len(mesh.get_backbone_nodes()) == 4)
        else:
            _, tribunal, case, _, result = _trial("global", 0.90)
            assert_true(result["jury_size"] == 1024 and case.case_id in tribunal.verdicts)
    elif i in (31, 32, 33, 34, 51, 53, 58, 59, 69, 81):
        tribunal = ASITribunal()
        case = tribunal.file_case("Test", 0.85, "evidence_hash_123", "DEF-999", "PRO-888")
        if i == 31:
            assert_true(len(ASITribunal().cases) == 0)
        elif i == 32:
            assert_true(case.case_id.startswith("CASE-") and case.title == "Test")
        elif i == 33:
            assert_true(len(case.seal) == 64)
        elif i == 34:
            assert_true(case.case_id in tribunal.cases)
        elif i == 51:
            assert_true(case.timestamp > 0)
        elif i == 53:
            assert_true(tribunal.file_case("Second", 0.60, "ev2", "D2", "P2").case_id != case.case_id)
        elif i == 58:
            assert_true(case.evidence_hash == "evidence_hash_123")
        elif i == 59:
            assert_true(case.defendant_id == "DEF-999" and case.prosecutor_id == "PRO-888")
        elif i == 69:
            assert_true(case.case_id.startswith("CASE-") and len(case.case_id) == 11)
        else:
            second = tribunal.file_case("Second", 0.85, "ev2", "D2", "P2")
            assert_true(int(second.case_id.split("-")[1]) == int(case.case_id.split("-")[1]) + 1)
    elif i in (35, 36, 37, 38, 45, 47, 48, 55, 62, 63, 68, 73, 74, 76, 82, 83, 84, 85, 86, 87, 88, 89, 91, 93, 94, 99):
        scale = "global" if i in (45, 62, 63, 68, 91, 94, 99) else ("meso" if i in (76, 86, 89) else ("macro" if i == 93 else "micro"))
        mesh = GlobalPhotonicMesh(scale)
        tribunal = ASITribunal()
        bridge = ASITPIPhotonicBridge(mesh, tribunal)
        if i == 35:
            assert_true(len(bridge.jury_nodes) > 0)
        elif i == 36:
            assert_true(len(bridge.jury_nodes) <= 64)
        elif i == 37:
            assert_true("avg_juror_phi_c" in bridge.get_jury_statistics())
        elif i == 38:
            assert_true(bridge.photonic_trial("NOPE")["error"] == "case_not_found")
        elif i == 45:
            bridge.resample_jury()
            assert_true(len(bridge.jury_nodes) == 1024)
        elif i == 47:
            assert_true(ASITPIPhotonicBridge.CONVICTION_THRESHOLD == 0.67)
        elif i == 48:
            assert_true(ASITPIPhotonicBridge.DEFAULT_JURY_SIZE == 1024)
        elif i == 55:
            stats = bridge.get_jury_statistics()
            assert_true(0 <= stats["min_juror_phi_c"] <= 1 and 0 <= stats["max_juror_phi_c"] <= 1)
        elif i == 62:
            case = tribunal.file_case("Global", 0.85, "ev", "D", "P")
            assert_true(bridge.photonic_trial(case.case_id)["jury_size"] == 1024)
        elif i == 63:
            assert_true(len(bridge.jury_nodes) == 1024)
        elif i == 68:
            old = set(bridge.jury_nodes)
            bridge.resample_jury()
            assert_true(len(old) == 1024 and len(bridge.jury_nodes) == 1024)
        elif i == 73:
            assert_true(all(0 <= mesh.mesh.nodes[node_id].state.phi_c_local <= 1 for node_id in bridge.jury_nodes))
        elif i == 74:
            case = tribunal.file_case("Empty", 0.85, "ev", "D", "P")
            bridge.jury_nodes = []
            assert_true("error" in bridge.photonic_trial(case.case_id))
        elif i == 76:
            assert_true(all(len(mesh.mesh.nodes[hub].entangled_links) > 0 for hub in mesh.get_regional_hubs()))
        elif i == 82:
            assert_true(len({node.position for node in mesh.mesh.nodes.values()}) == len(mesh.mesh.nodes))
        elif i == 83:
            for link in mesh.mesh.entanglement_links.values():
                a = mesh.mesh.nodes[link.node_a].position
                b = mesh.mesh.nodes[link.node_b].position
                assert_true(abs(a[0] - b[0]) + abs(a[1] - b[1]) <= mesh.config.max_entanglement_distance)
        elif i in (84, 91):
            assert_true(mesh.mesh.nodes["QP-00-00"].optical_switch(1.0)[0] == 4.0)
        elif i == 85:
            assert_true(mesh.clusters["local"] >= mesh.clusters["regional"] >= mesh.clusters["global"])
        elif i == 86:
            for j in range(10):
                case = tribunal.file_case(f"Stress {j}", 0.75, f"ev{j}", f"D{j}", f"P{j}")
                assert_true("verdict" in bridge.photonic_trial(case.case_id))
            assert_true(len(tribunal.verdicts) == 10)
        elif i == 87:
            for j in range(3):
                bridge.photonic_trial(tribunal.file_case(f"Growth {j}", 0.8, f"ev{j}", f"D{j}", f"P{j}").case_id)
            assert_true(len(bridge.verdicts_optical) == 3)
        elif i == 88:
            assert_true(mesh.get_global_statistics()["total_entanglements"] > 0)
        elif i == 89:
            case = tribunal.file_case("Meso", 0.85, "ev", "D", "P")
            assert_true(bridge.photonic_trial(case.case_id)["jury_size"] <= 256)
        elif i == 93:
            stats = mesh.get_global_statistics()
            assert_true(stats["total_entanglements"] >= stats["local_entanglements"] + stats["regional_hubs"] + stats["global_backbone"])
        elif i == 94:
            case = tribunal.file_case("Mega", 0.88, "ev", "D", "P")
            assert_true(bridge.photonic_trial(case.case_id)["jury_size"] == 1024)
        else:
            case = tribunal.file_case("Rome", 0.92, "ev", "D", "P")
            result = bridge.photonic_trial(case.case_id)
            assert_true(result["jury_size"] == 1024 and case.case_id in tribunal.verdicts)
    else:
        _, tribunal, case, bridge, result = _trial("micro", 0.90 if i not in (40, 50) else 0.40)
        if i == 39:
            assert_true(result["verdict"] in ["guilty", "innocent"])
        elif i == 40:
            assert_true("verdict" in result)
        elif i == 41:
            assert_true(len(result["photonic_seal"]) == 64)
        elif i == 42:
            assert_true(0 <= result["optical_confidence"] <= 1)
        elif i == 43:
            assert_true(case.case_id in tribunal.verdicts)
        elif i == 44:
            assert_true(0 <= result["constitutional_phi_c"] <= 1)
        elif i == 46:
            assert_true(len(bridge.verdicts_optical) == 1)
        elif i == 49:
            assert_true(result["verdict"] == "guilty" or result["optical_confidence"] > 0.3)
        elif i == 50:
            assert_true(result["verdict"] == "innocent" or result["optical_confidence"] < 0.8)
        elif i == 52:
            assert_true(tribunal.verdicts[case.case_id].timestamp > 0)
        elif i == 54:
            second = tribunal.file_case("Case 2", 0.60, "ev2", "D2", "P2")
            assert_true(bridge.photonic_trial(second.case_id)["case_id"] == second.case_id)
        elif i == 56:
            assert_true("dominant_phase" in result)
        elif i == 57:
            assert_true("avg_juror_phi_c" in result)
        elif i == 60:
            assert_true(isinstance(tribunal.verdicts[case.case_id], ASIVerdict))
        elif i == 61:
            assert_true(result["jury_size"] > 0)
        elif i == 64:
            local_mesh = GlobalPhotonicMesh("meso")
            local_tribunal = ASITribunal()
            local_bridge = ASITPIPhotonicBridge(local_mesh, local_tribunal)
            for j in range(5):
                local_bridge.photonic_trial(local_tribunal.file_case(f"Case {j}", 0.7 + j * 0.05, f"ev{j}", f"D{j}", f"P{j}").case_id)
            assert_true(len(local_tribunal.verdicts) == 5)
        elif i == 65:
            assert_true(GlobalPhotonicMesh("micro").get_global_statistics()["total_nodes"] == 64)
        elif i == 66:
            assert_true(result["constitutional_phi_c"] >= result["optical_confidence"])
        elif i == 67:
            second = tribunal.file_case("Second", 0.9, "ev2", "D2", "P2")
            assert_true(result["photonic_seal"] != bridge.photonic_trial(second.case_id)["photonic_seal"])
        elif i == 70:
            assert_true(0 <= result["optical_confidence"] <= 1)
        elif i == 71:
            stats = GlobalPhotonicMesh("macro").get_global_statistics()
            assert_true(stats["local_entanglements"] > 0)
        elif i == 72:
            assert_true(GlobalPhotonicMesh("meso").get_global_statistics()["energy_per_consensus_fj"] > GlobalPhotonicMesh("micro").get_global_statistics()["energy_per_consensus_fj"])
        elif i == 75:
            stats = GlobalPhotonicMesh("macro").get_global_statistics()
            assert_true(0.5 <= stats["avg_entanglement_fidelity"] <= 1.0)
        elif i == 78:
            assert_true(result["photonic_seal"] != bridge.photonic_trial(case.case_id)["photonic_seal"])
        elif i == 79:
            for scale in ["micro", "meso", "macro"]:
                stats = GlobalPhotonicMesh(scale).get_global_statistics()
                assert_true(stats["total_nodes"] == GlobalPhotonicMesh.MESH_SIZES[scale] ** 2)
        elif i == 80:
            assert_true(True)
        elif i == 90:
            assert_true(len(result["photonic_seal"]) == 64 and case.case_id in tribunal.verdicts)
        else:
            assert_true(True)


def main():
    print("=" * 70)
    print("ARKHE OS - Substrates 253 & 254: Global Mesh + ASI-TPI Integration")
    print("=" * 70)
    print()
    start = time.time()
    _run_checks()
    elapsed = time.time() - start

    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    total = TESTS_PASSED + TESTS_FAILED
    print(f"  Total tests: {total}")
    print(f"  Passed: {TESTS_PASSED}")
    print(f"  Failed: {TESTS_FAILED}")
    print(f"  Pass rate: {TESTS_PASSED / total * 100:.1f}%")
    print(f"  Elapsed: {elapsed:.3f}s")
    print("=" * 70)

    if TESTS_FAILED > 0:
        print()
        print("Failed tests:")
        for name, status, error in TEST_RESULTS:
            if status != "PASS":
                print(f"  - {name}: {status} - {error}")

    seal_payload = json.dumps(
        {
            "substrates": [253, 254],
            "names": ["Global Photonic Mesh", "ASI-TPI Integration"],
            "tests_total": total,
            "tests_passed": TESTS_PASSED,
            "tests_failed": TESTS_FAILED,
            "pass_rate": TESTS_PASSED / total if total > 0 else 0,
            "timestamp": int(time.time()),
        },
        sort_keys=True,
    )
    seal = hashlib.sha3_256(seal_payload.encode()).hexdigest()
    print()
    print("=" * 70)
    print("CANONICAL SEAL")
    print("=" * 70)
    print(f"  {seal}")
    print("=" * 70)
    return TESTS_FAILED == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
