"""
Kernel Isolation Engine — Substrato 989.z
Isolamento de regioes criticas do kernel da malha global, com barreiras de memoria,
traffic shaping, kill switch, probes temporais, e witnesses de transicao.
Deities: Proteus, Janus, Hecate, Morpheus
"""
import hashlib, json, time
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# ── Enums ───────────────────────────────────────────────────────────

class ZoneType(Enum):
    CRITICAL = "critical"
    RESILIENT = "resilient"
    ISOLATED = "isolated"

class RegionStatus(Enum):
    NOMINAL = "nominal"
    STRESSED = "stressed"
    ISOLATING = "isolating"
    LOCKED = "locked"
    RECOVERING = "recovering"

class FenceType(Enum):
    MEMORY = "memory"
    TRAFFIC = "traffic"
    KILL_SWITCH = "kill_switch"
    TEMPORAL = "temporal"

class AnomalySeverity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ── Data classes ────────────────────────────────────────────────────

@dataclass
class ZonePartition:
    zone_id: str
    zone_type: ZoneType
    substrates: List[int]
    status: RegionStatus = RegionStatus.NOMINAL
    parent_zone: Optional[str] = None
    resilience_level: int = 3
    isolation_history: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def compute_seal(self) -> str:
        p = {"zone_id": self.zone_id, "substrates": sorted(self.substrates), "status": self.status.value}
        return f"ZONE-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"

    @property
    def is_operational(self) -> bool:
        return self.status in {RegionStatus.NOMINAL, RegionStatus.STRESSED}


@dataclass
class MemoryFence:
    fence_id: str
    zone_id: str
    allocated_mb: float
    threshold_mb: float
    current_usage_mb: float = 0.0
    fence_type: FenceType = FenceType.MEMORY
    spillover_zone: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def usage_pct(self) -> float:
        return (self.current_usage_mb / self.threshold_mb * 100) if self.threshold_mb > 0 else 0

    @property
    def is_breached(self) -> bool:
        return self.current_usage_mb >= self.threshold_mb

    def seal(self) -> str:
        payload = json.dumps({
            "fence_id": self.fence_id,
            "zone_id": self.zone_id,
            "usage": self.current_usage_mb,
            "threshold": self.threshold_mb,
        }, sort_keys=True)
        return f"FENCE-{hashlib.sha3_256(payload.encode()).hexdigest()[:16].upper()}"


@dataclass
class TrafficShapingFence:
    fence_id: str
    zone_id: str
    max_packets_per_sec: int
    current_rate: int = 0
    burst_capacity: int = 100
    drops: int = 0
    fence_type: FenceType = FenceType.TRAFFIC

    @property
    def is_saturated(self) -> bool:
        return self.current_rate >= self.max_packets_per_sec

    def record_packet(self, packet_size: int = 1) -> bool:
        if self.current_rate + packet_size > self.max_packets_per_sec + self.burst_capacity:
            self.drops += 1
            return False
        self.current_rate = min(self.current_rate + packet_size, self.max_packets_per_sec + self.burst_capacity)
        return True

    def tick(self, decay: int = 10):
        self.current_rate = max(0, self.current_rate - decay)

    def seal(self) -> str:
        return f"TRAFFIC-{hashlib.sha3_256(json.dumps({'fence_id': self.fence_id, 'rate': self.current_rate, 'max': self.max_packets_per_sec, 'drops': self.drops}, sort_keys=True).encode()).hexdigest()[:16].upper()}"


@dataclass
class KillSwitch:
    switch_id: str
    zone_id: str
    armed: bool = False
    triggered: bool = False
    triggered_at: Optional[str] = None
    auto_arm_on_breach: bool = True
    cooldown_seconds: int = 300

    def arm(self) -> bool:
        if self.triggered:
            return False
        self.armed = True
        return True

    def disarm(self) -> bool:
        self.armed = False
        return True

    def trigger(self) -> bool:
        if not self.armed:
            return False
        self.armed = False
        self.triggered = True
        self.triggered_at = datetime.now(timezone.utc).isoformat()
        return True

    def seal(self) -> str:
        return f"KS-{hashlib.sha3_256(json.dumps({'switch_id': self.switch_id, 'zone_id': self.zone_id, 'armed': self.armed, 'triggered': self.triggered}, sort_keys=True).encode()).hexdigest()[:16].upper()}"


@dataclass
class TemporalProbe:
    probe_id: str
    zone_id: str
    origin_substrate: int
    target_substrate: int
    ttl_blocks: int = 10
    latency_ms: float = 0.0
    hops: int = 0
    coherence_at_source: float = 0.0
    coherence_at_target: float = 0.0
    is_ack: bool = False
    seal: str = ""

    def compute_seal(self) -> str:
        p = {"probe_id": self.probe_id, "zone_id": self.zone_id, "source": self.origin_substrate, "target": self.target_substrate}
        self.seal = f"PROBE-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"
        return self.seal


@dataclass
class TransitionWitness:
    witness_id: str
    zone_id: str
    from_status: RegionStatus
    to_status: RegionStatus
    triggered_by: str
    substrates_affected: List[int]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    seal: str = ""

    def compute_seal(self) -> str:
        p = {"witness_id": self.witness_id, "zone_id": self.zone_id, "from": self.from_status.value, "to": self.to_status.value}
        self.seal = f"WITNESS-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"
        return self.seal


@dataclass
class AnomalyRecord:
    anomaly_id: str
    zone_id: str
    severity: AnomalySeverity
    metric: str
    observed_value: float
    threshold_value: float
    description: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved: bool = False
    seal: str = ""

    def compute_seal(self) -> str:
        p = {"anomaly_id": self.anomaly_id, "zone_id": self.zone_id, "severity": self.severity.value, "metric": self.metric}
        self.seal = f"ANOM-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"
        return self.seal


# ── Core Engine ─────────────────────────────────────────────────────

class KernelIsolationEngine:
    SUBSTRATE_ID = "989.z"
    SEAL = "989.z-KERNEL-ISOLATION-ENGINE-F1A2B3C4D5E67890"

    def __init__(self):
        self.zones: Dict[str, ZonePartition] = {}
        self.memory_fences: Dict[str, MemoryFence] = {}
        self.traffic_fences: Dict[str, TrafficShapingFence] = {}
        self.kill_switches: Dict[str, KillSwitch] = {}
        self.temporal_probes: Dict[str, TemporalProbe] = {}
        self.witnesses: List[TransitionWitness] = []
        self.anomalies: Dict[str, AnomalyRecord] = {}
        self._anomaly_counter = 0
        self._witness_counter = 0
        self._probe_counter = 0
        self._fence_counter = 0
        self._switch_counter = 0

    def _next_id(self, prefix: str) -> str:
        c = getattr(self, f"_{prefix}_counter", 0) + 1
        setattr(self, f"_{prefix}_counter", c)
        return f"{prefix}-{c:06d}"

    # ── Zone Management ──────────────────────────────────────────

    def add_zone(self, zone_id: str, zone_type: ZoneType, substrates: List[int], parent: Optional[str] = None, resilience: int = 3) -> ZonePartition:
        z = ZonePartition(zone_id=zone_id, zone_type=zone_type, substrates=substrates, parent_zone=parent, resilience_level=resilience)
        self.zones[zone_id] = z
        return z

    def get_zone(self, zone_id: str) -> Optional[ZonePartition]:
        return self.zones.get(zone_id)

    def update_zone_status(self, zone_id: str, status: RegionStatus, triggered_by: str = "kernel") -> Optional[TransitionWitness]:
        z = self.get_zone(zone_id)
        if not z:
            return None
        old = z.status
        z.status = status
        z.isolation_history.append({"from": old.value, "to": status.value, "by": triggered_by, "at": datetime.now(timezone.utc).isoformat()})
        w = TransitionWitness(witness_id=self._next_id("witness"), zone_id=zone_id, from_status=old, to_status=status, triggered_by=triggered_by, substrates_affected=z.substrates)
        w.compute_seal()
        self.witnesses.append(w)
        return w

    def get_zone_map(self) -> Dict[str, Dict[str, Any]]:
        return {zid: {"type": z.zone_type.value, "status": z.status.value, "substrates": z.substrates, "resilience": z.resilience_level} for zid, z in self.zones.items()}

    # ── Memory Fences ────────────────────────────────────────────

    def create_memory_fence(self, zone_id: str, threshold_mb: float, allocated_mb: float, spillover: Optional[str] = None) -> MemoryFence:
        z = self.get_zone(zone_id)
        if not z:
            raise ValueError(f"Zone {zone_id} not found")
        f = MemoryFence(fence_id=self._next_id("fence"), zone_id=zone_id, threshold_mb=threshold_mb, allocated_mb=allocated_mb, spillover_zone=spillover)
        self.memory_fences[f.fence_id] = f
        return f

    def update_memory_usage(self, fence_id: str, usage_mb: float) -> Optional[AnomalyRecord]:
        f = self.memory_fences.get(fence_id)
        if not f:
            return None
        f.current_usage_mb = usage_mb
        if f.is_breached:
            a = AnomalyRecord(anomaly_id=self._next_id("anomaly"), zone_id=f.zone_id, severity=AnomalySeverity.HIGH, metric="memory_usage_pct", observed_value=f.usage_pct, threshold_value=100.0, description=f"Memory fence {fence_id} breached: {usage_mb:.1f}/{f.threshold_mb:.1f} MB")
            a.compute_seal()
            self.anomalies[a.anomaly_id] = a
            return a
        return None

    # ── Traffic Shaping ──────────────────────────────────────────

    def create_traffic_fence(self, zone_id: str, max_pps: int, burst: int = 100) -> TrafficShapingFence:
        z = self.get_zone(zone_id)
        if not z:
            raise ValueError(f"Zone {zone_id} not found")
        f = TrafficShapingFence(fence_id=self._next_id("fence"), zone_id=zone_id, max_packets_per_sec=max_pps, burst_capacity=burst)
        self.traffic_fences[f.fence_id] = f
        return f

    # ── Kill Switches ────────────────────────────────────────────

    def create_kill_switch(self, zone_id: str, auto_arm: bool = True, cooldown: int = 300) -> KillSwitch:
        z = self.get_zone(zone_id)
        if not z:
            raise ValueError(f"Zone {zone_id} not found")
        ks = KillSwitch(switch_id=self._next_id("switch"), zone_id=zone_id, auto_arm_on_breach=auto_arm, cooldown_seconds=cooldown)
        self.kill_switches[ks.switch_id] = ks
        return ks

    # ── Temporal Probes ──────────────────────────────────────────

    def send_probe(self, zone_id: str, origin: int, target: int, coherence_source: float, ttl: int = 10) -> TemporalProbe:
        z = self.get_zone(zone_id)
        if not z:
            raise ValueError(f"Zone {zone_id} not found")
        p = TemporalProbe(probe_id=self._next_id("probe"), zone_id=zone_id, origin_substrate=origin, target_substrate=target, ttl_blocks=ttl, coherence_at_source=coherence_source)
        p.compute_seal()
        self.temporal_probes[p.probe_id] = p
        return p

    def ack_probe(self, probe_id: str, coherence_target: float, latency_ms: float, hops: int) -> bool:
        p = self.temporal_probes.get(probe_id)
        if not p:
            return False
        p.coherence_at_target = coherence_target
        p.latency_ms = latency_ms
        p.hops = hops
        p.is_ack = True
        return True

    # ── Anomaly Detection ────────────────────────────────────────

    def detect_anomaly(self, zone_id: str, metric: str, observed: float, threshold: float, severity: AnomalySeverity, description: str) -> AnomalyRecord:
        a = AnomalyRecord(anomaly_id=self._next_id("anomaly"), zone_id=zone_id, severity=severity, metric=metric, observed_value=observed, threshold_value=threshold, description=description)
        a.compute_seal()
        self.anomalies[a.anomaly_id] = a
        return a

    def resolve_anomaly(self, anomaly_id: str) -> bool:
        a = self.anomalies.get(anomaly_id)
        if not a:
            return False
        a.resolved = True
        return True

    def get_active_anomalies(self) -> List[AnomalyRecord]:
        return [a for a in self.anomalies.values() if not a.resolved]

    # ── System Status ────────────────────────────────────────────

    def system_status(self) -> Dict[str, Any]:
        total_fences = len(self.memory_fences) + len(self.traffic_fences)
        breached = sum(1 for f in self.memory_fences.values() if f.is_breached)
        saturated = sum(1 for f in self.traffic_fences.values() if f.is_saturated)
        armed_ks = sum(1 for ks in self.kill_switches.values() if ks.armed)
        active_anomalies = len(self.get_active_anomalies())
        return {"zones": len(self.zones), "memory_fences": len(self.memory_fences), "traffic_fences": len(self.traffic_fences), "breached": breached, "saturated": saturated, "kill_switches": len(self.kill_switches), "armed_ks": armed_ks, "triggered_ks": sum(1 for ks in self.kill_switches.values() if ks.triggered), "probes_sent": len(self.temporal_probes), "probes_acked": sum(1 for p in self.temporal_probes.values() if p.is_ack), "witnesses": len(self.witnesses), "anomalies_total": len(self.anomalies), "anomalies_active": active_anomalies}

    def generate_report(self) -> str:
        s = self.system_status()
        lines = ["989.z-KERNEL-ISOLATION-ENGINE", f"Zones: {s['zones']} | Fences: {s['memory_fences']}+{s['traffic_fences']}", f"Breached: {s['breached']} | Saturated: {s['saturated']}", f"Kill Switches: {s['armed_ks']} armed / {s['triggered_ks']} triggered", f"Probes: {s['probes_acked']}/{s['probes_sent']} acked", f"Anomalies: {s['anomalies_active']} active / {s['anomalies_total']} total", f"Witnesses: {s['witnesses']} transitions recorded"]
        return "\n".join(lines)


__all__ = ["KernelIsolationEngine", "ZonePartition", "ZoneType", "RegionStatus", "MemoryFence", "TrafficShapingFence", "KillSwitch", "TemporalProbe", "TransitionWitness", "AnomalyRecord", "AnomalySeverity", "FenceType"]
