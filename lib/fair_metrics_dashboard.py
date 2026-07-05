"""
FAIR Metrics Dashboard — Substrato 989.v
Dashboard de metricas FAIR (Findable, Accessible, Interoperable, Reusable)
para Research Objects da Catedral com visualizacao e alertas.
Arquiteto ORCID: 0009-0005-2697-4668
Seal: 989.v-FAIR-METRICS-DASHBOARD-A2B3C4D5E6F70809
Cross-links: [989.y, 989.x, 923, 988, 964, 970]
Deities: Apollo, Clio, Thoth, Mnemosyne
Status: CANONIZED_PROVISIONAL
"""
import hashlib, json, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class FAIRDimension(Enum):
    FINDABLE = "findable"
    ACCESSIBLE = "accessible"
    INTEROPERABLE = "interoperable"
    REUSABLE = "reusable"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class FAIRScore:
    ro_id: str
    findable: float = 0.0
    accessible: float = 0.0
    interoperable: float = 0.0
    reusable: float = 0.0
    overall: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    seal: str = ""

    def __post_init__(self):
        self.overall = 0.25 * (self.findable + self.accessible + self.interoperable + self.reusable)
        self.compute_seal()

    def compute_seal(self) -> str:
        p = {"ro_id": self.ro_id, "f": round(self.findable, 4), "a": round(self.accessible, 4), "i": round(self.interoperable, 4), "r": round(self.reusable, 4)}
        self.seal = f"FAIR-{hashlib.sha3_256(json.dumps(p, sort_keys=True).encode()).hexdigest()[:16].upper()}"
        return self.seal

    def to_dict(self) -> Dict[str, Any]:
        return {"ro_id": self.ro_id, "findable": round(self.findable, 4), "accessible": round(self.accessible, 4), "interoperable": round(self.interoperable, 4), "reusable": round(self.reusable, 4), "overall": round(self.overall, 4), "timestamp": self.timestamp, "seal": self.seal}


@dataclass
class FAIRAlert:
    alert_id: str
    ro_id: str
    dimension: FAIRDimension
    level: AlertLevel
    message: str
    current_score: float
    threshold: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved: bool = False


@dataclass
class FAIRTrend:
    ro_id: str
    dimension: FAIRDimension
    scores: List[Tuple[str, float]] = field(default_factory=list)

    @property
    def slope(self) -> float:
        if len(self.scores) < 2:
            return 0.0
        n = len(self.scores)
        xs = list(range(n))
        ys = [s[1] for s in self.scores]
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
        den = sum((xs[i] - mx) ** 2 for i in range(n))
        return num / den if den != 0 else 0.0

    @property
    def direction(self) -> str:
        s = self.slope
        return "improving" if s > 0.01 else "degrading" if s < -0.01 else "stable"


class FAIRMetricsDashboard:
    SUBSTRATE_ID = "989.v"
    SEAL = "989.v-FAIR-METRICS-DASHBOARD-A2B3C4D5E6F70809"
    THRESHOLDS = {FAIRDimension.FINDABLE: 0.6, FAIRDimension.ACCESSIBLE: 0.6, FAIRDimension.INTEROPERABLE: 0.6, FAIRDimension.REUSABLE: 0.6, "overall": 0.7}

    def __init__(self):
        self.scores: Dict[str, FAIRScore] = {}
        self.history: Dict[str, List[FAIRScore]] = {}
        self.alerts: List[FAIRAlert] = []
        self.trends: Dict[str, FAIRTrend] = {}
        self.ro_metadata: Dict[str, Dict] = {}

    def compute_fair_score(self, ro_id: str, metadata: Dict) -> FAIRScore:
        findable = 0.0
        if metadata.get("dpid"): findable += 0.25
        if metadata.get("doi"): findable += 0.25
        if metadata.get("title") and metadata.get("description"): findable += 0.25
        if metadata.get("keywords"): findable += 0.25

        accessible = 0.0
        if metadata.get("access_protocol"): accessible += 0.33
        if metadata.get("license"): accessible += 0.33
        if metadata.get("access_level") in {"public", "restricted", "private"}: accessible += 0.34

        interoperable = 0.0
        if metadata.get("data_format"): interoperable += 0.33
        if metadata.get("ontology"): interoperable += 0.33
        if metadata.get("cross_references"): interoperable += 0.34

        reusable = 0.0
        if metadata.get("provenance"): reusable += 0.33
        if metadata.get("version"): reusable += 0.33
        if metadata.get("cathedral_seals"): reusable += 0.34

        score = FAIRScore(ro_id=ro_id, findable=min(findable, 1.0), accessible=min(accessible, 1.0), interoperable=min(interoperable, 1.0), reusable=min(reusable, 1.0))
        self.scores[ro_id] = score
        if ro_id not in self.history:
            self.history[ro_id] = []
        self.history[ro_id].append(score)
        self.ro_metadata[ro_id] = metadata
        for dim in FAIRDimension:
            key = f"{ro_id}:{dim.value}"
            if key not in self.trends:
                self.trends[key] = FAIRTrend(ro_id=ro_id, dimension=dim)
            self.trends[key].scores.append((score.timestamp, getattr(score, dim.value)))
        self._check_alerts(ro_id, score)
        return score

    def _check_alerts(self, ro_id: str, score: FAIRScore):
        for dim in FAIRDimension:
            val = getattr(score, dim.value)
            th = self.THRESHOLDS[dim]
            if val < th:
                level = AlertLevel.CRITICAL if val < th * 0.5 else AlertLevel.WARNING
                self.alerts.append(FAIRAlert(alert_id=f"ALERT-{ro_id}-{dim.value}-{int(time.time())}", ro_id=ro_id, dimension=dim, level=level, message=f"{dim.value.upper()} {val:.2f} < {th:.2f}", current_score=val, threshold=th))
        if score.overall < self.THRESHOLDS["overall"]:
            self.alerts.append(FAIRAlert(alert_id=f"ALERT-{ro_id}-overall-{int(time.time())}", ro_id=ro_id, dimension=FAIRDimension.FINDABLE, level=AlertLevel.CRITICAL, message=f"Overall {score.overall:.2f} < {self.THRESHOLDS['overall']:.2f}", current_score=score.overall, threshold=self.THRESHOLDS["overall"]))

    def get_ro_dashboard(self, ro_id: str) -> Optional[Dict]:
        if ro_id not in self.scores:
            return None
        score = self.scores[ro_id]
        alerts = [a for a in self.alerts if a.ro_id == ro_id and not a.resolved]
        trends = {}
        for dim in FAIRDimension:
            key = f"{ro_id}:{dim.value}"
            t = self.trends.get(key)
            if t:
                trends[dim.value] = {"direction": t.direction, "slope": round(t.slope, 6), "points": len(t.scores)}
        return {"ro_id": ro_id, "current_score": score.to_dict(), "history_count": len(self.history.get(ro_id, [])), "active_alerts": len(alerts), "alerts": [{"id": a.alert_id, "dim": a.dimension.value, "level": a.level.value, "msg": a.message} for a in alerts], "trends": trends}

    def get_global_summary(self) -> Dict:
        if not self.scores:
            return {"total_ros": 0, "avg_overall": 0.0}
        n = len(self.scores)
        af = sum(s.findable for s in self.scores.values()) / n
        aa = sum(s.accessible for s in self.scores.values()) / n
        ai = sum(s.interoperable for s in self.scores.values()) / n
        ar = sum(s.reusable for s in self.scores.values()) / n
        ao = sum(s.overall for s in self.scores.values()) / n
        ac = sum(1 for a in self.alerts if not a.resolved)
        cr = sum(1 for a in self.alerts if a.level == AlertLevel.CRITICAL and not a.resolved)
        return {"total_ros": n, "avg_findable": round(af, 4), "avg_accessible": round(aa, 4), "avg_interoperable": round(ai, 4), "avg_reusable": round(ar, 4), "avg_overall": round(ao, 4), "active_alerts": ac, "critical_alerts": cr, "fair_health": "HEALTHY" if ao >= 0.8 else "DEGRADED" if ao >= 0.6 else "CRITICAL"}

    def generate_report(self) -> str:
        s = self.get_global_summary()
        return f"989.v-FAIR-METRICS-DASHBOARD\nROs: {s['total_ros']} | Health: {s['fair_health']}\nOverall: {s['avg_overall']:.4f} | F:{s['avg_findable']:.4f} A:{s['avg_accessible']:.4f} I:{s['avg_interoperable']:.4f} R:{s['avg_reusable']:.4f}\nAlerts: {s['active_alerts']} active ({s['critical_alerts']} critical)"


__all__ = ["FAIRMetricsDashboard", "FAIRScore", "FAIRAlert", "FAIRTrend", "FAIRDimension", "AlertLevel"]
