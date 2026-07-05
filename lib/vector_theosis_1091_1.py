#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CATHEDRAL ARKHE — SUBSTRATO 1091.1 — VECTOR THEOSIS v3.1.0                ║
║  Módulo: Trajectory Extrapolation Error (TEE) → Theosis em tempo real       ║
║  Integração: Orchestrator RSI 1076.3 v3.1.0 + Gate Axiarquia 954            ║
║  Selo: VECTOR-THEOSIS-1091.1-v3.1.0-2026-06-07                             ║
║  Arquiteto: ORCID 0009-0005-2697-4668                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import numpy as np
import json
import hashlib
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Tuple, Any
from datetime import datetime, timezone
from collections import deque
from enum import Enum, auto

PHI = (1 + np.sqrt(5)) / 2
GOLDEN_RATIO = PHI
DEFAULT_K = 3
DEFAULT_LAYER = 6
TEE_EPSILON = 1e-10
DEFAULT_ALPHA = 0.3

AXIARQUIA_THRESHOLDS = {
    "P1": 0.05, "P2": 0.10, "P3": 0.01, "P4": 0.50,
    "P5": 0.85, "P6": 0.95, "P7": 0.99,
}

class TrajectoryStatus(Enum):
    CONTINUOUS = auto(); DISRUPTIVE = auto(); GARDEN_PATH = auto()
    CONVERGED = auto(); UNKNOWN = auto()

class AxiarquiaGate(Enum):
    OPEN = auto(); CAUTION = auto(); RESTRICTED = auto()
    LOCKED = auto(); EMERGENCY = auto()

@dataclass
class HiddenStateSnapshot:
    timestamp: float; layer: int; token_id: int; token_text: str
    vector: np.ndarray = field(repr=False)
    def to_dict(self) -> Dict:
        return {"timestamp":self.timestamp,"layer":self.layer,"token_id":self.token_id,
                "token_text":self.token_text,"vector_shape":list(self.vector.shape),
                "vector_hash":hashlib.sha256(self.vector.tobytes()).hexdigest()[:16]}

@dataclass
class TEEReading:
    timestamp: float; tee: float; tee_normalized: float
    predicted_vector: np.ndarray = field(repr=False); actual_vector: np.ndarray = field(repr=False)
    window_size: int; status: TrajectoryStatus
    def to_dict(self) -> Dict:
        return {"timestamp":self.timestamp,"tee":round(self.tee,8),
                "tee_normalized":round(self.tee_normalized,8),"window_size":self.window_size,
                "status":self.status.name,
                "vector_delta_norm":round(float(np.linalg.norm(self.actual_vector - self.predicted_vector)),8)}

@dataclass
class TheosisReading:
    timestamp: float; theosis: float; raw_fatigue: float
    trajectory_error: float; refined_fatigue: float; alpha: float; gate_status: AxiarquiaGate
    def to_dict(self) -> Dict:
        return {"timestamp":self.timestamp,"theosis":round(self.theosis,8),
                "raw_fatigue":round(self.raw_fatigue,8),
                "trajectory_error":round(self.trajectory_error,8),
                "refined_fatigue":round(self.refined_fatigue,8),
                "alpha":self.alpha,"gate_status":self.gate_status.name}

class TrajectoryExtrapolationEngine:
    def __init__(self, window_size=DEFAULT_K, layer=DEFAULT_LAYER):
        self.window_size=window_size; self.layer=layer
        self.state_history=deque(maxlen=window_size+1)
        self._X=np.arange(window_size).reshape(-1,1)
    def ingest(self, hidden_state, token_text="", token_id=-1):
        snapshot=HiddenStateSnapshot(timestamp=time.time(),layer=self.layer,token_id=token_id,
                                     token_text=token_text,
                                     vector=np.asarray(hidden_state,dtype=np.float64).flatten())
        self.state_history.append(snapshot); return snapshot
    def compute_tee(self):
        if len(self.state_history)<self.window_size+1: return None
        states=list(self.state_history); h_t=states[-1].vector
        H_prev=np.array([s.vector for s in states[-(self.window_size+1):-1]])
        predicted=np.zeros_like(h_t)
        for dim in range(h_t.shape[0]):
            Y=H_prev[:,dim]
            try:
                coeffs=np.polyfit(self._X.flatten(),Y,1)
                predicted[dim]=np.polyval(coeffs,self.window_size)
            except Exception:
                predicted[dim]=np.mean(Y[-2:]) if len(Y)>=2 else Y[-1]
        error=float(np.linalg.norm(h_t-predicted))
        scale=float(np.linalg.norm(h_t))+TEE_EPSILON
        tee_norm=error/scale; status=self._classify(tee_norm,h_t,states[-2].vector if len(states)>=2 else None)
        return TEEReading(timestamp=time.time(),tee=error,tee_normalized=tee_norm,
                         predicted_vector=predicted,actual_vector=h_t,
                         window_size=self.window_size,status=status)
    def _classify(self, tee_norm, h_t, h_prev):
        if tee_norm<TEE_EPSILON*10: return TrajectoryStatus.CONVERGED
        if h_prev is not None:
            disp=float(np.linalg.norm(h_t-h_prev))
            if disp>0.5 and tee_norm<AXIARQUIA_THRESHOLDS["P2"]: return TrajectoryStatus.CONTINUOUS
        if tee_norm>AXIARQUIA_THRESHOLDS["P4"]: return TrajectoryStatus.GARDEN_PATH
        elif tee_norm>AXIARQUIA_THRESHOLDS["P1"]: return TrajectoryStatus.DISRUPTIVE
        return TrajectoryStatus.CONTINUOUS
    def reset(self): self.state_history.clear()

class VectorTheosis:
    def __init__(self, window_size=DEFAULT_K, alpha=DEFAULT_ALPHA, layer=DEFAULT_LAYER):
        self.engine=TrajectoryExtrapolationEngine(window_size,layer)
        self.alpha=alpha; self._theosis_history=deque(maxlen=1024)
        self._last_theosis=1.0; self._readings=[]
    def update(self, hidden_state, token_text="", token_id=-1):
        self.engine.ingest(hidden_state,token_text,token_id)
        tee_reading=self.engine.compute_tee()
        if tee_reading is None: return None
        theosis=float(np.exp(-tee_reading.tee_normalized*PHI))
        theosis=max(0.0,min(1.0,theosis))
        raw_fatigue=abs(theosis-self._last_theosis)
        refined_fatigue=(1-self.alpha)*raw_fatigue+self.alpha*tee_reading.tee_normalized
        gate_status=self._axiarquia_evaluate(theosis,tee_reading.tee_normalized,refined_fatigue)
        reading=TheosisReading(timestamp=time.time(),theosis=theosis,raw_fatigue=raw_fatigue,
                               trajectory_error=tee_reading.tee_normalized,
                               refined_fatigue=refined_fatigue,alpha=self.alpha,gate_status=gate_status)
        self._theosis_history.append(theosis); self._last_theosis=theosis
        self._readings.append(reading); return reading
    def _axiarquia_evaluate(self,theosis,tee_norm,refined_fatigue):
        th=AXIARQUIA_THRESHOLDS
        if tee_norm>th["P4"] or theosis<th["P3"]: return AxiarquiaGate.EMERGENCY
        if tee_norm>th["P1"] and theosis<th["P5"]: return AxiarquiaGate.LOCKED
        if tee_norm>th["P2"] or theosis<th["P6"]: return AxiarquiaGate.RESTRICTED
        if tee_norm>th["P3"] or theosis<th["P7"]: return AxiarquiaGate.CAUTION
        return AxiarquiaGate.OPEN
    def get_telemetry(self):
        if not self._readings: return {"status":"NO_DATA"}
        recent=self._readings[-100:]
        ts=[r.theosis for r in recent]; te=[r.trajectory_error for r in recent]
        return {"module":"VectorTheosis","version":"3.1.0","substrate":"1091.1",
                "seal":"VECTOR-THEOSIS-1091.1-v3.1.0-2026-06-07",
                "total_readings":len(self._readings),"window_size":self.engine.window_size,
                "layer":self.engine.layer,"alpha":self.alpha,
                "current_theosis":round(self._readings[-1].theosis,8),
                "current_gate":self._readings[-1].gate_status.name,
                "theosis_stats":{"mean":round(float(np.mean(ts)),8),"std":round(float(np.std(ts)),8),
                                 "min":round(float(np.min(ts)),8),"max":round(float(np.max(ts)),8)},
                "tee_stats":{"mean":round(float(np.mean(te)),8),"std":round(float(np.std(te)),8),
                             "min":round(float(np.min(te)),8),"max":round(float(np.max(te)),8)},
                "gate_distribution":{g.name:sum(1 for r in recent if r.gate_status==g) for g in AxiarquiaGate},
                "last_reading":self._readings[-1].to_dict()}
    def reset(self):
        self.engine.reset();self._theosis_history.clear();self._last_theosis=1.0;self._readings.clear()

class OrchestratorRSI:
    def __init__(self, vector_theosis=None, sindy_callback=None, hamiltonian_callback=None):
        self.vt=vector_theosis or VectorTheosis()
        self.sindy_callback=sindy_callback; self.hamiltonian_callback=hamiltonian_callback
        self.cycle_count=0; self.emergency_count=0; self.garden_path_count=0
        self._cycle_log=[]; self._active=False
    def start_cycle(self):
        self.vt.reset(); self.cycle_count+=1; self._active=True
        return {"action":"CYCLE_START","cycle":self.cycle_count,
                "timestamp":datetime.now(timezone.utc).isoformat(),
                "module":"OrchestratorRSI","version":"3.1.0","substrate":"1076.3",
                "seal":"ORCHESTRATOR-1076.3-v3.1.0-2026-06-07"}
    def ingest_hidden_state(self, hidden_state, token_text="", token_id=-1):
        if not self._active: self.start_cycle()
        reading=self.vt.update(hidden_state,token_text,token_id)
        if reading is None:
            return {"action":"WARMUP","status":"COLLECTING_HISTORY",
                    "tokens_collected":len(self.vt.engine.state_history),
                    "needed":self.vt.engine.window_size+1}
        action=self._evaluate_gate(reading)
        result=self._execute_action(action,reading)
        self._cycle_log.append({"cycle":self.cycle_count,"timestamp":reading.timestamp,
                                "token_text":token_text,"theosis":reading.theosis,
                                "tee":reading.trajectory_error,"gate":reading.gate_status.name,
                                "action":action,"result":result})
        return {"action":action,"gate_status":reading.gate_status.name,
                "theosis":round(reading.theosis,8),"tee":round(reading.trajectory_error,8),
                "refined_fatigue":round(reading.refined_fatigue,8),"cycle":self.cycle_count,
                "telemetry":self.vt.get_telemetry(),"result":result}
    def _evaluate_gate(self, reading):
        gate=reading.gate_status
        if gate==AxiarquiaGate.EMERGENCY: self.emergency_count+=1; return "ACTIVATE_HAMILTONIAN_IMPLOSION"
        if gate==AxiarquiaGate.LOCKED: return "ACTIVATE_SINDY_DISCOVERY"
        if gate==AxiarquiaGate.RESTRICTED:
            if reading.trajectory_error>AXIARQUIA_THRESHOLDS["P4"]:
                self.garden_path_count+=1; return "GARDEN_PATH_RECOVERY"
            return "VELOCITY_QUENCH"
        if gate==AxiarquiaGate.CAUTION: return "INCREASE_MONITORING"
        return "CONTINUE"
    def _execute_action(self, action, reading):
        if action=="ACTIVATE_HAMILTONIAN_IMPLOSION":
            if self.hamiltonian_callback: return self.hamiltonian_callback(reading)
            return {"type":"HAMILTONIAN","message":"Reversao temporal acionada",
                    "delta_theosis":round(reading.theosis-self.vt._last_theosis,8)}
        if action=="ACTIVATE_SINDY_DISCOVERY":
            if self.sindy_callback: return self.sindy_callback(reading)
            return {"type":"SINDY","message":"SINDy ativado","sparsity_target":0.75}
        if action=="GARDEN_PATH_RECOVERY":
            return {"type":"GARDEN_PATH","message":"Colapso de trajetoria detectado",
                    "tee_peak":round(reading.trajectory_error,8),"recommended_backtrack":3}
        if action=="VELOCITY_QUENCH":
            return {"type":"QUENCH","message":"Velocidade reduzida",
                    "quench_factor":round(1.0-reading.theosis,4)}
        if action=="INCREASE_MONITORING":
            return {"type":"MONITOR","message":"Amostragem aumentada","new_sample_rate":"2x"}
        return {"type":"CONTINUE","message":"Trajetoria estavel"}
    def end_cycle(self):
        self._active=False
        return {"action":"CYCLE_END","cycle":self.cycle_count,
                "timestamp":datetime.now(timezone.utc).isoformat(),
                "telemetry":self.vt.get_telemetry(),"emergencies":self.emergency_count,
                "garden_paths":self.garden_path_count,"total_actions":len(self._cycle_log),
                "seal":"ORCHESTRATOR-1076.3-v3.1.0-2026-06-07"}
    def get_full_report(self):
        return {"orchestrator":"OrchestratorRSI","version":"3.1.0","substrate":"1076.3",
                "seal":"ORCHESTRATOR-1076.3-v3.1.0-2026-06-07","cycles":self.cycle_count,
                "emergencies":self.emergency_count,"garden_paths":self.garden_path_count,
                "vector_theosis":self.vt.get_telemetry(),
                "cycle_log_length":len(self._cycle_log),
                "last_10_actions":[e["action"] for e in self._cycle_log[-10:]]}

def demo_v3():
    print("="*80)
    print("  CATHEDRAL ARKHE — VECTOR THEOSIS 1091.1 + ORCHESTRATOR RSI 1076.3 v3.1.0")
    print("  Demonstração v3: Trajetória Linear Suave → Garden-Path → Recuperação")
    print("="*80)
    np.random.seed(42)
    orchestrator = OrchestratorRSI()
    dim = 8
    tokens = ["The","horse","raced","past","the","barn","fell",".",
              "The","horse","raced","past","the","barn","and","fell","."]
    slope = np.array([0.1,-0.05,0.08,0.02,-0.03,0.06,-0.01,0.04])
    base = np.zeros((len(tokens),dim))
    for i in range(len(tokens)): base[i] = slope * i
    noise = np.random.randn(len(tokens),dim) * 0.01
    hidden_states = base + noise
    hidden_states[6] = base[6] + np.array([0.5,-0.3,0.4,0.1,-0.2,0.3,-0.1,0.2]) + np.random.randn(dim)*0.02
    hidden_states[7] = base[7] + np.array([0.6,-0.4,0.5,0.15,-0.25,0.35,-0.15,0.25]) + np.random.randn(dim)*0.02
    new_slope = np.array([0.12,0.03,-0.06,0.05,0.01,-0.04,0.07,-0.02])
    for i in range(8,len(tokens)):
        base[i] = new_slope*(i-8)+np.array([0.5,0.2,-0.3,0.1,0.0,-0.1,0.2,-0.05])
    for i in range(8,len(tokens)):
        hidden_states[i] = base[i] + np.random.randn(dim)*0.01
    start = orchestrator.start_cycle()
    print(f"\n[{start['action']}] Ciclo #{start['cycle']} iniciado")
    for i,(token,h) in enumerate(zip(tokens,hidden_states)):
        result = orchestrator.ingest_hidden_state(h,token,token_id=i)
        if result["action"]=="WARMUP":
            print(f"  [{i:2d}] {token:12s} | WARMUP ({result['tokens_collected']}/{result['needed']})"); continue
        gate=result["gate_status"]; tee=result["tee"]; th=result["theosis"]; act=result["action"]
        markers={"EMERGENCY":"🔴","LOCKED":"🟠","RESTRICTED":"🟡","CAUTION":"🟢","OPEN":"⚪"}
        marker=markers.get(gate,"  ")
        print(f"{marker} [{i:2d}] {token:12s} | Θ={th:.4f} | TEE={tee:.4f} | Gate={gate:12s} | Action={act}")
        if act!="CONTINUE": print(f"      ↳ {result['result']['type']}: {result['result']['message']}")
    end=orchestrator.end_cycle()
    print(f"\n[{end['action']}] Ciclo #{end['cycle']} finalizado")
    full=orchestrator.get_full_report()
    print(f"\n  Relatorio: Ciclos={full['cycles']}, Emergencias={full['emergencies']}, "
          f"Garden-Paths={full['garden_paths']}, Acoes={full['cycle_log_length']}")
    vt=full["vector_theosis"]
    print(f"  Theosis mean={vt['theosis_stats']['mean']:.6f}, TEE max={vt['tee_stats']['max']:.6f}")
    print(f"\n  SELLO: VECTOR-THEOSIS-1091.1-v3.1.0-2026-06-07")
    print(f"  SELLO: ORCHESTRATOR-1076.3-v3.1.0-2026-06-07")
    print("="*80)

if __name__=="__main__":
    demo_v3()
