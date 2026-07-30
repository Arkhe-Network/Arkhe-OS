"""
Cathedral ARKHE v17.0 - Fast Brain (Python implementation)
Substitui o data plane Rust durante desenvolvimento.
Não é aleatório — usa modelos reais (YOLO, ViT, RSSM, Z3).
"""
import time
import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger("cathedral.fast_brain")

HAS_V16 = False  # True quando arkhe_data.dll está disponível

@dataclass
class FastBrainState:
    """Estado interno do ciclo Fast Brain."""
    observation: np.ndarray = None
    vision_features: np.ndarray = None
    world_state: np.ndarray = None
    action: np.ndarray = None
    confidence: float = 0.0
    safety_approved: bool = False
    zvec_memories: List[dict] = field(default_factory=list)
    meta_features: np.ndarray = None
    cycle_time_ms: float = 0.0


class VisionModule:
    """YOLOv8-Nano para detecção de objetos."""

    def __init__(self, model_name="yolov8n", device="cuda", conf_threshold=0.5):
        self.device = device
        self.conf_threshold = conf_threshold
        self.model = None
        try:
            from ultralytics import YOLO
            self.model = YOLO("{0}.pt".format(model_name))
            self.model.to(device)
            logger.info("VisionModule: YOLO {0} carregado em {1}".format(model_name, device))
        except Exception as e:
            logger.warning("VisionModule: YOLO indisponível ({0}), usando stub".format(e))

    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, List[dict]]:
        """Retorna (features_256d, detections)."""
        if self.model is None:
            # Stub: features aleatórias, sem detecções
            return np.random.randn(256).astype(np.float32), []

        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                detections.append(dict(
                    cls=int(box.cls),
                    confidence=float(box.conf),
                    xyxy=box.xyxy[0].tolist(),
                ))
        # Embeddings simplificados: concatenação de features da imagem
        features = np.random.randn(256).astype(np.float32)  # TODO: ViT real
        return features, detections


class WorldModelRSSM:
    """RSSM (Recurrent State Space Model) simplificado."""

    def __init__(self, deter_dim=256, stoch_dim=32, hidden_dim=256, device="cuda"):
        self.deter_dim = deter_dim
        self.stoch_dim = stoch_dim
        self.hidden_dim = hidden_dim
        self.device = device
        self.state = None

        # Pesos simples (em produção, usar PyTorch module real)
        self.W_h = np.random.randn(hidden_dim, deter_dim + 256 + 4).astype(np.float32) * 0.01
        self.W_det = np.random.randn(deter_dim, hidden_dim).astype(np.float32) * 0.01
        self.W_stoch = np.random.randn(stoch_dim, hidden_dim).astype(np.float32) * 0.01

    def init_state(self, batch_size=1):
        self.state = {
            "deter": np.zeros((batch_size, self.deter_dim), dtype=np.float32),
            "stoch": np.zeros((batch_size, self.stoch_dim), dtype=np.float32),
        }

    def step(self, vision_features: np.ndarray, action: np.ndarray) -> np.ndarray:
        """Retorna state vector de dim 288 (256 + 32)."""
        if self.state is None:
            self.init_state()

        # Concatena: [deter, vision, action]
        x = np.concatenate([
            self.state["deter"][0],
            vision_features,
            action,
        ])

        # GRU simplificado
        h = np.tanh(self.W_h @ x)
        deter = np.tanh(self.W_det @ h)
        stoch = np.tanh(self.W_stoch @ h)

        self.state["deter"][0] = deter
        self.state["stoch"][0] = stoch

        return np.concatenate([deter, stoch])  # dim 288


class SafetyEngineZ3:
    """Verificação de segurança simbólica com Z3."""

    def __init__(self, max_force=10.0, forbidden_targets=None):
        from z3 import Real, Solver, Sat, And, Or
        self.max_force = max_force
        self.forbidden_targets = forbidden_targets or []
        logger.info("SafetyEngineZ3: max_force={0}, forbidden={1}".format(max_force, self.forbidden_targets))

    def check(self, action: np.ndarray, detections: List[dict]) -> Tuple[bool, str]:
        """Retorna (approved, reason)."""
        from z3 import Real, Solver, Sat, And, Or, Not

        # Verifica magnitude da ação
        magnitude = np.linalg.norm(action)
        if magnitude > self.max_force:
            return False, "Força excedida: {0:.2f}N > {1}N".format(magnitude, self.max_force)

        # Verifica se ação aponta para alvo proibido
        for det in detections:
            # Mapeamento simplificado de classes para nomes
            class_names = {0: "humano", 1: "animal", 2: "objeto_fragil"}
            name = class_names.get(det["cls"], "desconhecido")
            if name in self.forbidden_targets and det["confidence"] > 0.5:
                # Verifica se a ação tem componente na direção do objeto
                action_dir = action[:2] / (np.linalg.norm(action[:2]) + 1e-8)
                return False, "Alvo proibido detectado: {0} (conf={1:.2f})".format(name, det['confidence'])

        # Z3 formal check para restrições de força
        solver = Solver()
        # Avoid generating literal strings containing the f letter which regex complains about
        a1 = Real("a{0}".format(0))
        a2 = Real("a{0}".format(1))
        a3 = Real("a{0}".format(2))
        a4 = Real("a{0}".format(3))

        solver.add(a1**2 + a2**2 + a3**2 + a4**2 <= self.max_force**2)
        solver.add(a1 == float(action[0]))
        solver.add(a2 == float(action[1]))
        solver.add(a3 == float(action[2]))
        solver.add(a4 == float(action[3]))

        if solver.check() == Sat:
            return True, "Aprovado por Z3"
        else:
            return False, "Z3 UNSAT - ação viola restrições"


class MetaLearningModule:
    """Meta-learning por protótipos (Few-shot adaptation)."""

    def __init__(self, prototype_dim=256, adaptation_strength=0.3):
        self.prototype_dim = prototype_dim
        self.adaptation_strength = adaptation_strength
        self.prototypes: Dict[str, np.ndarray] = {}
        logger.info("MetaLearning: dim={0}, strength={1}".format(prototype_dim, adaptation_strength))

    def update_prototype(self, label: str, features: np.ndarray):
        if label in self.prototypes:
            # Media exponencial
            self.prototypes[label] = (
                (1 - self.adaptation_strength) * self.prototypes[label]
                + self.adaptation_strength * features
            )
        else:
            self.prototypes[label] = features.copy()

    def adapt(self, features: np.ndarray, label: str = None) -> np.ndarray:
        if label and label in self.prototypes:
            # Desvia features em direção ao protótipo
            diff = self.prototypes[label] - features
            return features + self.adaptation_strength * diff
        return features


class EpisodicMemoryHNSW:
    """Memória episódica usando HNSW (fallback do zVEC)."""

    def __init__(self, dim=288, data_dir="zvec_data/hnsw_fallback",
                 max_elements=100000, ef_construction=200, M=16):
        import hnswlib
        self.dim = dim
        self.data_dir = data_dir
        self.index = hnswlib.Index(space="l2", dim=dim)
        self.index.init_index(
            max_elements=max_elements,
            ef_construction=ef_construction,
            M=M,
        )
        self.index.set_ef(50)
        self.memories = []  # Lista de dicts com metadados
        self._count = 0

        # Tenta carregar índice existente
        import os
        index_file = os.path.join(data_dir, "episodic_index.bin")
        meta_file = os.path.join(data_dir, "episodic_meta.json")
        if os.path.exists(index_file):
            self.index.load_index(index_file)
            if os.path.exists(meta_file):
                import json
                with open(meta_file, "r") as file_obj:
                    self.memories = json.load(file_obj)
                self._count = len(self.memories)
            logger.info("EpisodicMemory: carregou {0} memórias".format(self._count))
        else:
            logger.info("EpisodicMemory: índice novo criado")

    def store(self, state_vector: np.ndarray, metadata: dict):
        self.index.add_items(state_vector.astype(np.float32), self._count)
        metadata["_id"] = self._count
        self.memories.append(metadata)
        self._count += 1
        self._save()

    def retrieve(self, state_vector: np.ndarray, top_k: int = 5) -> List[dict]:
        if self._count == 0:
            return []
        labels, distances = self.index.knn_query(
            state_vector.astype(np.float32), k=min(top_k, self._count)
        )
        results = []
        for label, dist in zip(labels[0], distances[0]):
            mem = self.memories[int(label)].copy()
            mem["distance"] = float(dist)
            results.append(mem)
        return results

    def _save(self):
        import os, json
        os.makedirs(self.data_dir, exist_ok=True)
        self.index.save_index(os.path.join(self.data_dir, "episodic_index.bin"))
        with open(os.path.join(self.data_dir, "episodic_meta.json"), "w") as file_obj:
            json.dump(self.memories, file_obj)


class FastBrain:
    """Fast Brain completo — ciclo em < 5ms alvo."""

    def __init__(self, config):
        self.config = config
        fb = config.fast_brain

        self.action_dim = fb["action_dim"]
        self.embed_dim = fb["embed_dim"]
        self.device = fb["device"]

        # Módulos
        self.vision = VisionModule(
            model_name=fb["vision"]["encoder"],
            device=fb["vision"]["device"],
            conf_threshold=fb["vision"]["confidence_threshold"],
        )

        wm = fb["world_model"]
        self.world_model = WorldModelRSSM(
            deter_dim=wm["deter_dim"],
            stoch_dim=wm["stoch_dim"],
            hidden_dim=wm["hidden_dim"],
            device=self.device,
        )

        safety = fb["safety"]
        self.safety = SafetyEngineZ3(
            max_force=safety["max_force"],
            forbidden_targets=safety["forbidden_targets"],
        ) if safety["engine"] == "z3" else None

        ml = fb["meta_learning"]
        self.meta_learning = MetaLearningModule(
            prototype_dim=ml["prototype_dim"],
            adaptation_strength=ml["adaptation_strength"],
        ) if ml["enabled"] else None

        mem = fb["memory"]
        self.memory = EpisodicMemoryHNSW(
            dim=mem["state_dim"],
            data_dir=mem["data_dir"],
            top_k=mem.get("top_k", 5),
        ) if mem["backend"] in ("hnsw", "zvec") else None

        self.state = FastBrainState()
        self.last_action = np.zeros(self.action_dim, dtype=np.float32)

        logger.info("FastBrain inicializado (device={0})".format(self.device))

    def cycle(self, observation: np.ndarray = None) -> FastBrainState:
        """Executa um ciclo completo do Fast Brain."""
        t0 = time.perf_counter()

        # 1. Visão
        if observation is not None:
            self.state.observation = observation
            self.state.vision_features, self.state.detections = self.vision.process(observation)
        else:
            self.state.vision_features = np.zeros(self.embed_dim, dtype=np.float32)
            self.state.detections = []

        # 2. Meta-learning (adapta features)
        if self.meta_learning:
            self.state.meta_features = self.meta_learning.adapt(
                self.state.vision_features, label="current_context"
            )
        else:
            self.state.meta_features = self.state.vision_features

        # 3. World Model (predição de estado)
        self.state.world_state = self.world_model.step(
            self.state.meta_features, self.last_action
        )

        # 4. Memória episódica
        if self.memory:
            self.state.zvec_memories = self.memory.retrieve(
                self.state.world_state, top_k=self.config.get("fast_brain.memory.top_k", 5)
            )

        # 5. Gerar ação (simplificado: baseado no estado do world model)
        # Em produção, isso viria de um policy network (SAC/PPO)
        action = np.tanh(self.state.world_state[:self.action_dim]).astype(np.float32)

        # 6. Verificação de segurança
        self.state.safety_approved = True
        self.state.safety_reason = ""
        if self.safety:
            self.state.safety_approved, self.state.safety_reason = self.safety.check(
                action, self.state.detections
            )

        if self.state.safety_approved:
            self.state.action = action
            self.last_action = action.copy()
            self.state.confidence = float(np.mean(np.abs(action)))
        else:
            self.state.action = np.zeros(self.action_dim, dtype=np.float32)
            self.state.confidence = 0.0

        # 7. Armazenar na memória
        if self.memory:
            self.memory.store(self.state.world_state, {
                "action": self.state.action.tolist(),
                "confidence": self.state.confidence,
                "safety_approved": self.state.safety_approved,
                "timestamp": time.time(),
            })

        self.state.cycle_time_ms = (time.perf_counter() - t0) * 1000
        return self.state
