"""
Unified Orchestrator — Substrato 989.w
Orquestra unificada de todos os substratos 989.x/989.y/989.z
com health checks, circuit breakers, metricas e auto-healing.
Arquiteto ORCID: 0009-0005-2697-4668
Seal: 989.w-UNIFIED-ORCHESTRATOR-F3A4B5C6D7E8F901
Cross-links: [989.x, 989.y, 989.z, 989.x.1, 989.x.2, 989.x.3, 989.x.4, 970, 972, 964]
Deities: Zeus, Athena, Hermes, Hephaestus
Status: CANONIZED_PROVISIONAL
"""
import asyncio, hashlib, json, time
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class SubstrateStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class HealthCheck:
    substrate_id: str
    timestamp: str
    latency_ms: float
    status: SubstrateStatus
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreaker:
    substrate_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure: Optional[str] = None
    last_success: Optional[str] = None
    threshold: int = 5
    timeout_seconds: int = 30
    half_open_max: int = 3


@dataclass
class OrchestratorMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    circuit_breaks: int = 0
    auto_heals: int = 0
    theosis: float = 0.0
    entropy: float = 0.0
    resilience: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_requests, 1)

    @property
    def success_rate(self) -> float:
        return self.successful_requests / max(self.total_requests, 1)

    @property
    def availability(self) -> float:
        return 1.0 - (self.failed_requests / max(self.total_requests, 1))


class UnifiedOrchestrator:
    SUBSTRATE_ID = "989.w"
    SEAL = "989.w-UNIFIED-ORCHESTRATOR-F3A4B5C6D7E8F901"
    MANAGED_SUBSTRATES = ["989.x", "989.x.1", "989.x.2", "989.x.3", "989.x.4", "989.y", "989.z", "970", "972", "964"]

    def __init__(self):
        self.substrates: Dict[str, Any] = {}
        self.health_checks: Dict[str, List[HealthCheck]] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.metrics = OrchestratorMetrics()
        self.logs: List[str] = []
        self.is_running = False
        self._tasks: Set[asyncio.Task] = set()
        for sid in self.MANAGED_SUBSTRATES:
            self.circuit_breakers[sid] = CircuitBreaker(substrate_id=sid, threshold=5, timeout_seconds=30)
            self.health_checks[sid] = []

    def log(self, msg: str):
        t = datetime.now(timezone.utc).isoformat()
        entry = f"[{t}] [ORCH] {msg}"
        self.logs.append(entry)

    def register_substrate(self, substrate_id: str, instance: Any) -> bool:
        if substrate_id not in self.MANAGED_SUBSTRATES:
            return False
        self.substrates[substrate_id] = instance
        return True

    async def health_check(self, substrate_id: str) -> HealthCheck:
        start = time.time()
        instance = self.substrates.get(substrate_id)
        if not instance:
            lat = (time.time() - start) * 1000
            return HealthCheck(substrate_id=substrate_id, timestamp=datetime.now(timezone.utc).isoformat(), latency_ms=lat, status=SubstrateStatus.OFFLINE, error="Not registered")
        try:
            if hasattr(instance, "generate_report"):
                instance.generate_report()
            lat = (time.time() - start) * 1000
            return HealthCheck(substrate_id=substrate_id, timestamp=datetime.now(timezone.utc).isoformat(), latency_ms=lat, status=SubstrateStatus.HEALTHY)
        except Exception as e:
            lat = (time.time() - start) * 1000
            return HealthCheck(substrate_id=substrate_id, timestamp=datetime.now(timezone.utc).isoformat(), latency_ms=lat, status=SubstrateStatus.UNHEALTHY, error=str(e))

    async def run_all_health_checks(self) -> Dict[str, HealthCheck]:
        results = {}
        for sid in self.substrates:
            ck = await self.health_check(sid)
            results[sid] = ck
            self.health_checks[sid].append(ck)
            self.health_checks[sid] = self.health_checks[sid][-100:]
            self._update_circuit_breaker(sid, ck)
        return results

    def _update_circuit_breaker(self, sid: str, ck: HealthCheck):
        cb = self.circuit_breakers[sid]
        if cb.state == CircuitState.CLOSED:
            if ck.status in {SubstrateStatus.UNHEALTHY, SubstrateStatus.OFFLINE}:
                cb.failure_count += 1
                cb.last_failure = ck.timestamp
                if cb.failure_count >= cb.threshold:
                    cb.state = CircuitState.OPEN
                    self.metrics.circuit_breaks += 1
            else:
                cb.success_count += 1
                cb.last_success = ck.timestamp
                cb.failure_count = max(0, cb.failure_count - 1)
        elif cb.state == CircuitState.OPEN:
            if cb.last_failure:
                last = datetime.fromisoformat(cb.last_failure.replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - last).total_seconds() > cb.timeout_seconds:
                    cb.state = CircuitState.HALF_OPEN
                    cb.failure_count = 0
                    cb.success_count = 0
        elif cb.state == CircuitState.HALF_OPEN:
            if ck.status in {SubstrateStatus.UNHEALTHY, SubstrateStatus.OFFLINE}:
                cb.failure_count += 1
                if cb.failure_count >= cb.half_open_max:
                    cb.state = CircuitState.OPEN
            else:
                cb.success_count += 1
                if cb.success_count >= cb.half_open_max:
                    cb.state = CircuitState.CLOSED
                    cb.failure_count = 0
                    self.metrics.auto_heals += 1

    def can_execute(self, substrate_id: str) -> bool:
        cb = self.circuit_breakers.get(substrate_id)
        if not cb:
            return True
        return cb.state in {CircuitState.CLOSED, CircuitState.HALF_OPEN}

    async def execute(self, substrate_id: str, operation: str, *args, **kwargs) -> Any:
        self.metrics.total_requests += 1
        start = time.time()
        if not self.can_execute(substrate_id):
            self.metrics.failed_requests += 1
            self.metrics.total_latency_ms += (time.time() - start) * 1000
            raise Exception(f"Circuit breaker OPEN for {substrate_id}")
        instance = self.substrates.get(substrate_id)
        if not instance:
            self.metrics.failed_requests += 1
            self.metrics.total_latency_ms += (time.time() - start) * 1000
            raise Exception(f"Substrate {substrate_id} not registered")
        try:
            method = getattr(instance, operation, None)
            if not method:
                raise Exception(f"Operation {operation} not found on {substrate_id}")
            result = await method(*args, **kwargs) if hasattr(method, '__await__') else method(*args, **kwargs)
            self.metrics.successful_requests += 1
            self.metrics.total_latency_ms += (time.time() - start) * 1000
            return result
        except Exception as e:
            self.metrics.failed_requests += 1
            self.metrics.total_latency_ms += (time.time() - start) * 1000
            ck = await self.health_check(substrate_id)
            self._update_circuit_breaker(substrate_id, ck)
            raise

    async def auto_heal(self):
        for sid, cb in self.circuit_breakers.items():
            if cb.state == CircuitState.OPEN:
                ck = await self.health_check(sid)
                self._update_circuit_breaker(sid, ck)

    async def monitor_loop(self, interval_seconds: int = 10):
        self.is_running = True
        while self.is_running:
            await self.run_all_health_checks()
            await self.auto_heal()
            self._compute_global_metrics()
            await asyncio.sleep(interval_seconds)

    def _compute_global_metrics(self):
        total = len(self.substrates)
        if total == 0:
            return
        healthy = sum(1 for chk in self.health_checks.values() if chk and chk[-1].status == SubstrateStatus.HEALTHY)
        degraded = sum(1 for chk in self.health_checks.values() if chk and chk[-1].status == SubstrateStatus.DEGRADED)
        unhealthy = sum(1 for chk in self.health_checks.values() if chk and chk[-1].status == SubstrateStatus.UNHEALTHY)
        self.metrics.theosis = healthy / total
        self.metrics.entropy = (degraded + unhealthy) / total
        self.metrics.resilience = 1.0 - (unhealthy / total)
        self.metrics.timestamp = datetime.now(timezone.utc).isoformat()

    def stop(self):
        self.is_running = False

    def generate_report(self) -> str:
        self._compute_global_metrics()
        m = self.metrics
        lines = [f"989.w-UNIFIED-ORCHESTRATOR", f"Theosis: {m.theosis:.4f} | Entropy: {m.entropy:.4f} | Resilience: {m.resilience:.4f}", f"Requests: {m.total_requests} (ok:{m.successful_requests} fail:{m.failed_requests})", f"Avg Latency: {m.avg_latency_ms:.2f}ms | Availability: {m.availability:.4f}", f"Circuit Breaks: {m.circuit_breaks} | Auto Heals: {m.auto_heals}"]
        for sid, cb in self.circuit_breakers.items():
            lines.append(f"  {sid}: {cb.state.value.upper()} (f:{cb.failure_count} s:{cb.success_count})")
        return "\n".join(lines)


__all__ = ["UnifiedOrchestrator", "HealthCheck", "CircuitBreaker", "OrchestratorMetrics", "SubstrateStatus", "CircuitState"]
