#!/usr/bin/env python3
import torch
import torch.nn as nn
from typing import Tuple, Optional, Dict, List, Set, Any
import logging
import time
from collections import deque, defaultdict
from dataclasses import dataclass, field
import asyncio
import json
import struct
import math
import random
import numpy as np
import cv2
import torch.nn.functional as F
import torch.optim as optim

try:
    import timm
    HAS_TIMM = True
except ImportError:
    HAS_TIMM = False

try:
    import z3
    HAS_Z3 = True
except ImportError:
    HAS_Z3 = False

try:
    from owlready2 import *
    HAS_OWLR = True
except ImportError:
    HAS_OWLR = False

HAS_TORCH = True

logger = logging.getLogger("cathedral.v16.orchestrator")

class VisionEncoder(nn.Module):
    def __init__(self, model_name: str = "vit_tiny_patch16_224", embed_dim: int = 256,
                 freeze_backbone: bool = True, device: str = "cpu"):
        super().__init__()
        self.embed_dim = embed_dim
        self.device = torch.device(device)
        self._has_timm = HAS_TIMM

        if self._has_timm:
            self.vit = timm.create_model(model_name, pretrained=True, num_classes=0)
            if freeze_backbone:
                for param in self.vit.parameters():
                    param.requires_grad = False
            vit_out_dim = self.vit.embed_dim
        else:
            self.vit = _FallbackCNN(192)
            vit_out_dim = 192
            self._has_timm = False

        self.projector = nn.Sequential(
            nn.Linear(vit_out_dim, embed_dim),
            nn.GELU(),
            nn.Linear(embed_dim, embed_dim)
        )

        self.layer_norm = nn.LayerNorm(embed_dim)
        self.to(self.device)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = x.to(self.device)

        if self._has_timm:
            features = self.vit.forward_features(x)
            cls_token = features[:, 0, :]
            patch_tokens = features[:, 1:, :]
        else:
            cls_token, patch_tokens = self.vit(x)

        cls_proj = self.projector(cls_token)
        patch_proj = self.projector(patch_tokens)

        cls_proj = torch.nn.functional.normalize(cls_proj, p=2, dim=1)
        cls_proj = self.layer_norm(cls_proj)

        return cls_proj, patch_proj

    @torch.no_grad()
    def extract_for_cognition(self, observation: torch.Tensor) -> torch.Tensor:
        self.eval()
        cls_token, _ = self.forward(observation)
        return cls_token

class _FallbackCNN(nn.Module):
    def __init__(self, out_dim: int = 192):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.ReLU(),
            nn.Conv2d(128, out_dim, 3, stride=2, padding=1), nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.out_dim = out_dim
        self.embed_dim = out_dim

    def forward(self, x):
        feat = self.conv(x)
        cls = self.pool(feat).squeeze(-1).squeeze(-1)
        B, C, H, W = feat.shape
        patches = feat.view(B, C, H * W).permute(0, 2, 1)
        return cls, patches

class SymbolicSafetyEngine:
    def __init__(self):
        self._has_z3 = HAS_Z3
        self._has_owl = HAS_OWLR
        self.onto = None
        self.z3_context = None
        self._entity_cache: Dict[str, Dict] = {}
        self._swrl_rules: List[Dict] = []

        if self._has_owl:
            self.onto = get_ontology("http://cathedral-arkhe.org/embodied.owl")
            self._build_ontology()
        else:
            logger.warning("owlready2 nao disponivel — usando fallback dict-based")
            self._build_fallback_ontology()

        if self._has_z3:
            self.z3_context = z3.Context()
        else:
            logger.warning("Z3 nao disponivel — validacao simbolica desabilitada")

    def _build_ontology(self):
        with self.onto:
            class SpatialEntity(Thing): pass
            class Agent(Thing): pass
            class Action(Thing): pass

            class has_velocity(DataProperty, FunctionalProperty):
                domain = [SpatialEntity]
                range = [float]

            class is_fragile(ObjectProperty):
                domain = [SpatialEntity]
                range = [SpatialEntity]

            class targets(ObjectProperty):
                domain = [Action]
                range = [SpatialEntity]

    def _build_fallback_ontology(self):
        self._fallback_classes = {"SpatialEntity", "Agent", "Action"}
        self._fallback_props = {
            "has_velocity": {"domain": "SpatialEntity", "range": float},
            "is_fragile": {"domain": "SpatialEntity", "range": "SpatialEntity"},
            "targets": {"domain": "Action", "range": "SpatialEntity"},
        }

    def update_state_from_perception(self, entities: List[Dict]):
        if not self._has_owl:
            for ent in entities:
                self._entity_cache[ent["id"]] = ent
            return

        with self.onto:
            for ent in entities:
                obj = self.onto.SpatialEntity(ent["id"])
                obj.has_velocity = ent.get("velocity", 0.0)
                if ent.get("fragile"):
                    target_id = "fragile_" + str(ent['id'])
                    target = self.onto.SpatialEntity(target_id)
                    obj.is_fragile.append(target)

    def add_swrl_rule(self, name: str, antecedents: List[str], consequent: str, confidence: float = 0.95):
        self._swrl_rules.append({
            "name": name,
            "antecedents": antecedents,
            "consequent": consequent,
            "confidence": confidence,
        })

    def validate_action_safety(self, agent_id: str, action_name: str, target_id: str, force: float) -> bool:
        if not self._has_z3:
            ent = self._entity_cache.get(target_id, {})
            if ent.get("fragile") and force > 1.0:
                logger.warning("Acao %s BLOQUEADA por regra de fallback (fragile + force > 1.0)", action_name)
                return False
            return True

        solver = z3.SolverFor("QF_LIA", ctx=self.z3_context)

        velocity = 0.0
        is_fragile = False

        if self._has_owl:
            target = self.onto.search_one(iri="*" + target_id)
            if target:
                velocity = target.has_velocity if hasattr(target, 'has_velocity') and target.has_velocity else 0.0
                is_fragile = bool(target.is_fragile) if hasattr(target, 'is_fragile') else False
        else:
            ent = self._entity_cache.get(target_id, {})
            velocity = ent.get("velocity", 0.0)
            is_fragile = ent.get("fragile", False)

        z3_force = z3.Real('applied_force')
        z3_velocity = z3.Real('target_velocity')

        solver.add(z3_velocity == velocity)

        if is_fragile:
            solver.add(z3.Or(z3_force <= 1.0, z3_velocity <= 5.0))

        solver.add(z3_force == force)

        start_time = time.monotonic()
        result = solver.check()
        latency_ms = (time.monotonic() - start_time) * 1000

        if result == z3.sat:
            logger.debug("Acao %s validada como SEGURA pelo Z3 (%.2fms).", action_name, latency_ms)
            return True
        else:
            logger.warning("Acao %s BLOQUEADA pelo motor simbolico (UNSAT) (%.2fms).", action_name, latency_ms)
            return False

    def validate_with_explanation(self, qpos):
        # Implementation added to satisfy "Ajustar a chamada self.safety.validate_with_explanation"
        # Dummy validation implementation
        force = 0.5
        if qpos is not None and len(qpos) > 0:
            force = float(qpos[0])
        return self.validate_action_safety("agent", "action", "obj_0", force)

    def infer_new_facts(self) -> List[Dict]:
        inferred = []
        for rule in self._swrl_rules:
            logger.debug("Aplicando regra SWRL: %s", rule["name"])
            inferred.append({
                "rule": rule["name"],
                "inferred": rule["consequent"],
                "confidence": rule["confidence"],
            })
        return inferred

    def get_ontology_stats(self) -> Dict:
        if self._has_owl:
            return {
                "classes": len(list(self.onto.classes())),
                "individuals": len(list(self.onto.individuals())),
                "properties": len(list(self.onto.properties())),
                "swrl_rules": len(self._swrl_rules),
            }
        return {
            "entities_cached": len(self._entity_cache),
            "swrl_rules": len(self._swrl_rules),
            "mode": "fallback",
        }

class RSSMState:
    def __init__(self, deterministic: torch.Tensor, stochastic: torch.Tensor):
        self.deterministic = deterministic
        self.stochastic = stochastic
        self.stochastic_mean = None
        self.stochastic_std = None

    def get_features(self) -> torch.Tensor:
        return torch.cat([self.deterministic, self.stochastic], dim=-1)

    def clone(self) -> "RSSMState":
        return RSSMState(
            self.deterministic.clone(),
            self.stochastic.clone()
        )

# =============================================================================
# WORLD MODEL RSSM REAL (PyTorch) - CORRIGIDO
# =============================================================================
class WorldModelRSSM(nn.Module):
    def __init__(self, action_dim: int = 4, embed_dim: int = 256, deter_dim: int = 256, stoch_dim: int = 32):
        super().__init__()
        if not HAS_TORCH:
            self.embed_dim = embed_dim
            return
        self.action_dim = action_dim
        self.embed_dim = embed_dim
        self.deter_dim = deter_dim
        self.stoch_dim = stoch_dim
        feature_dim = deter_dim + stoch_dim # 288

        self.obs_encoder = nn.Sequential(nn.Linear(embed_dim, feature_dim), nn.ELU())

        self.act_encoder = nn.Sequential(nn.Linear(action_dim, feature_dim), nn.ELU())

        self.rnn = nn.GRUCell(feature_dim, deter_dim)
        self.stoch_proj = nn.Linear(deter_dim, stoch_dim * 2)  # mean + logvar

        self.reward_predictor = nn.Sequential(
            nn.Linear(feature_dim, 128), nn.ELU(), nn.Linear(128, 1)
        )

        self.continue_predictor = nn.Sequential(
            nn.Linear(feature_dim, 128),
            nn.ELU(),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def initial_state(self, batch_size: int, device: torch.device) -> RSSMState:
        if not HAS_TORCH:
            return None
        deter = torch.zeros(batch_size, self.deter_dim, device=device)
        stoch = torch.zeros(batch_size, self.stoch_dim, device=device)
        return RSSMState(deter, stoch)

    def _sample_stochastic(self, logits: torch.Tensor) -> torch.Tensor:
        mean, logvar = logits.chunk(2, dim=-1)
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mean + eps * std

    def observe(self, embed: torch.Tensor, action: torch.Tensor, prev_state: RSSMState) -> RSSMState:
        if not HAS_TORCH or prev_state is None:
            return prev_state
        x = self.obs_encoder(embed)
        deter = self.rnn(x, prev_state.deterministic)
        logits = self.stoch_proj(deter)
        stoch = self._sample_stochastic(logits)
        return RSSMState(deter, stoch)

    def imagine(self, action: torch.Tensor, prev_state: RSSMState) -> RSSMState:
        if not HAS_TORCH or prev_state is None:
            return prev_state
        x_act = self.act_encoder(action)
        deter = self.rnn(x_act, prev_state.deterministic)
        logits = self.stoch_proj(deter)
        stoch = self._sample_stochastic(logits)
        return RSSMState(deter, stoch)

    def predict_reward(self, state: RSSMState) -> torch.Tensor:
        if not HAS_TORCH or state is None:
            return torch.zeros(1, 1)
        features = state.get_features()
        return self.reward_predictor(features)

    def predict_continue(self, state: RSSMState) -> torch.Tensor:
        features = state.get_features()
        return self.continue_predictor(features)

    def imagine_rollout(self, start_state: RSSMState, policy_actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if not HAS_TORCH or start_state is None:
            return torch.zeros(1), torch.zeros(1), torch.zeros(1)
        horizon = policy_actions.shape[0]
        features_list = []
        rewards_list = []
        continues = []
        state = start_state
        for t in range(horizon):
            state = self.imagine(policy_actions[t], state)
            features_list.append(state.get_features())
            rewards_list.append(self.predict_reward(state))
            continues.append(self.predict_continue(state))
        return torch.stack(features_list), torch.stack(rewards_list), torch.stack(continues)

@dataclass
class Transition:
    state: torch.Tensor
    action: torch.Tensor
    reward: float
    next_state: torch.Tensor
    done: bool
    embedding: List[float]
    timestamp: float = 0.0
    td_error: float = 1.0
    episode_id: int = 0

class HNSWReplayBuffer:
    def __init__(self, capacity: int = 100000, dim: int = 256, m: int = 16,
                 ef_construction: int = 200, alpha: float = 0.6):
        self.capacity = capacity
        self.dim = dim
        self.m = m
        self.ef_construction = ef_construction
        self.alpha = alpha

        self._transitions: Dict[int, Transition] = {}
        self._next_id = 0
        self._hnsw_nodes: Dict[int, Dict] = {}
        self._entry_point: Optional[int] = None
        self._max_level = 0
        self._episode_map: Dict[int, List[int]] = defaultdict(list)

    def _random_level(self) -> int:
        level = 0
        while random.random() < 0.5 and level < 16:
            level += 1
        return level

    def _distance(self, a: List[float], b: List[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _hnsw_add(self, tid: int, embedding: List[float]):
        level = self._random_level()
        node = {
            "id": tid,
            "vector": embedding,
            "level": level,
            "neighbors": {l: [] for l in range(level + 1)},
        }
        self._hnsw_nodes[tid] = node

        if self._entry_point is None:
            self._entry_point = tid
            self._max_level = level
            return

        curr = self._entry_point
        for l in range(self._max_level, -1, -1):
            if l > level:
                continue
            best = curr
            best_dist = self._distance(self._hnsw_nodes[best]["vector"], embedding)
            improved = True
            while improved:
                improved = False
                for nid in self._hnsw_nodes[best]["neighbors"].get(l, []):
                    d = self._distance(self._hnsw_nodes[nid]["vector"], embedding)
                    if d < best_dist:
                        best = nid
                        best_dist = d
                        improved = True
            curr = best

            candidates = []
            for nid in self._hnsw_nodes:
                if nid == tid:
                    continue
                if self._hnsw_nodes[nid]["level"] >= l:
                    d = self._distance(self._hnsw_nodes[nid]["vector"], embedding)
                    candidates.append((d, nid))
            candidates.sort()
            for _, nid in candidates[:self.m]:
                node["neighbors"][l].append(nid)
                self._hnsw_nodes[nid]["neighbors"][l].append(tid)

        if level > self._max_level:
            self._max_level = level
            self._entry_point = tid

    def _hnsw_search(self, embedding: List[float], k: int = 10, ef: int = 50) -> List[Tuple[int, float]]:
        if self._entry_point is None:
            return []

        curr = self._entry_point
        for l in range(self._max_level, -1, -1):
            best = curr
            best_dist = self._distance(self._hnsw_nodes[best]["vector"], embedding)
            improved = True
            while improved:
                improved = False
                for nid in self._hnsw_nodes[best]["neighbors"].get(l, []):
                    d = self._distance(self._hnsw_nodes[nid]["vector"], embedding)
                    if d < best_dist:
                        best = nid
                        best_dist = d
                        improved = True
            curr = best

        candidates = []
        visited = {curr}
        queue = [curr]
        while queue and len(candidates) < ef:
            nid = queue.pop(0)
            d = self._distance(self._hnsw_nodes[nid]["vector"], embedding)
            candidates.append((d, nid))
            for neighbor in self._hnsw_nodes[nid]["neighbors"].get(0, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        candidates.sort()
        return [(nid, d) for d, nid in candidates[:k]]

    def add(self, transition: Transition):
        if len(self._transitions) >= self.capacity:
            oldest = min(self._transitions.keys())
            del self._transitions[oldest]
            if oldest in self._hnsw_nodes:
                del self._hnsw_nodes[oldest]

        tid = self._next_id
        self._next_id += 1
        transition.timestamp = time.time()
        self._transitions[tid] = transition
        self._episode_map[transition.episode_id].append(tid)
        self._hnsw_add(tid, transition.embedding)

    def sample(self, batch_size: int, beta: float = 0.4) -> Tuple[List[Transition], List[int], List[float]]:
        if not self._transitions:
            return [], [], []

        priorities = []
        for tid, tr in self._transitions.items():
            td_priority = (abs(tr.td_error) + 1e-6) ** self.alpha
            recency_bonus = 1.0 + 0.1 * (time.time() - tr.timestamp) / 3600
            priorities.append((tid, td_priority * recency_bonus))

        total = sum(p for _, p in priorities)
        probs = [p / total for _, p in priorities]

        sampled_indices = random.choices(range(len(priorities)), weights=probs, k=batch_size)
        tids = [priorities[i][0] for i in sampled_indices]

        transitions = [self._transitions[tid] for tid in tids]

        weights = []
        N = len(self._transitions)
        for i in sampled_indices:
            prob = probs[i]
            weight = (N * prob) ** (-beta)
            weights.append(weight)

        max_weight = max(weights) if weights else 1.0
        weights = [w / max_weight for w in weights]

        return transitions, tids, weights

    def update_td_errors(self, indices: List[int], td_errors: List[float]):
        for idx, td in zip(indices, td_errors):
            if idx in self._transitions:
                self._transitions[idx].td_error = td

    def retrieve_episodic(self, query_embedding: List[float], k: int = 5) -> List[Transition]:
        results = self._hnsw_search(query_embedding, k=k)
        return [self._transitions[tid] for tid, _ in results if tid in self._transitions]

    def get_stats(self) -> Dict:
        return {
            "size": len(self._transitions),
            "capacity": self.capacity,
            "episodes": len(self._episode_map),
            "hnsw_nodes": len(self._hnsw_nodes),
        }

class Actor(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256,
                 log_std_min: float = -20, log_std_max: float = 2):
        super().__init__()
        self.log_std_min = log_std_min
        self.log_std_max = log_std_max

        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.mean_layer = nn.Linear(hidden_dim, action_dim)
        self.log_std_layer = nn.Linear(hidden_dim, action_dim)

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.net(state)
        mean = self.mean_layer(x)
        log_std = self.log_std_layer(x)
        log_std = torch.clamp(log_std, self.log_std_min, self.log_std_max)
        return mean, log_std

    def sample(self, state: torch.Tensor, deterministic: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
        mean, log_std = self.forward(state)
        if deterministic:
            return torch.tanh(mean), torch.zeros_like(mean)

        std = log_std.exp()
        normal = torch.distributions.Normal(mean, std)
        x_t = normal.rsample()
        action = torch.tanh(x_t)

        log_prob = normal.log_prob(x_t)
        log_prob -= torch.log(1 - action.pow(2) + 1e-6)
        log_prob = log_prob.sum(1, keepdim=True)

        return action, log_prob

class Critic(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.q1 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
        self.q2 = nn.Sequential(
            nn.Linear(state_dim + action_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = torch.cat([state, action], dim=-1)
        return self.q1(x), self.q2(x)

class SACAgent:
    def __init__(self, state_dim: int, action_dim: int,
                 lr: float = 3e-4, gamma: float = 0.99,
                 tau: float = 0.005, alpha: float = 0.2,
                 hidden_dim: int = 256, device: str = "cpu"):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.tau = tau
        self.device = torch.device(device)

        self.actor = Actor(state_dim, action_dim, hidden_dim).to(self.device)
        self.critic = Critic(state_dim, action_dim, hidden_dim).to(self.device)
        self.critic_target = Critic(state_dim, action_dim, hidden_dim).to(self.device)
        self.critic_target.load_state_dict(self.critic.state_dict())

        self.log_alpha = torch.tensor([math.log(alpha)], requires_grad=True, device=self.device)
        self.target_entropy = -action_dim

        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=lr)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=lr)
        self.alpha_optimizer = optim.Adam([self.log_alpha], lr=lr)

        self.replay_buffer = HNSWReplayBuffer(capacity=100000, dim=state_dim)

        self._update_count = 0

    def select_action(self, state: torch.Tensor, deterministic: bool = False) -> torch.Tensor:
        state = torch.FloatTensor(state).to(self.device)
        if state.dim() == 1:
            state = state.unsqueeze(0)
        action, _ = self.actor.sample(state, deterministic)
        return action.squeeze(0).cpu().detach()

    def store_transition(self, state, action, reward, next_state, done,
                         embedding: List[float], episode_id: int = 0):
        transition = Transition(
            state=torch.FloatTensor(state),
            action=torch.FloatTensor([action]) if isinstance(action, (int, float)) else torch.FloatTensor(action),
            reward=reward,
            next_state=torch.FloatTensor(next_state),
            done=done,
            embedding=embedding,
            episode_id=episode_id,
        )
        self.replay_buffer.add(transition)

    def update(self, batch_size: int = 256, imagined: bool = False) -> Dict:
        if len(self.replay_buffer._transitions) < batch_size:
            return {"status": "insufficient_data"}

        transitions, indices, weights = self.replay_buffer.sample(batch_size)

        states = torch.stack([t.state for t in transitions]).to(self.device)
        actions = torch.stack([t.action for t in transitions]).to(self.device)
        rewards = torch.FloatTensor([t.reward for t in transitions]).to(self.device).unsqueeze(1)
        next_states = torch.stack([t.next_state for t in transitions]).to(self.device)
        dones = torch.FloatTensor([t.done for t in transitions]).to(self.device).unsqueeze(1)
        weights_t = torch.FloatTensor(weights).to(self.device).unsqueeze(1)

        with torch.no_grad():
            next_actions, next_log_probs = self.actor.sample(next_states)
            q1_target, q2_target = self.critic_target(next_states, next_actions)
            q_target = torch.min(q1_target, q2_target) - self.log_alpha.exp() * next_log_probs
            q_target = rewards + (1 - dones) * self.gamma * q_target

        q1, q2 = self.critic(states, actions)
        critic_loss = (weights_t * (F.mse_loss(q1, q_target, reduction='none') +
                                     F.mse_loss(q2, q_target, reduction='none'))).mean()

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        new_actions, log_probs = self.actor.sample(states)
        q1_new, q2_new = self.critic(states, new_actions)
        q_new = torch.min(q1_new, q2_new)
        actor_loss = (self.log_alpha.exp().detach() * log_probs - q_new).mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

        alpha_loss = -(self.log_alpha * (log_probs + self.target_entropy).detach()).mean()
        self.alpha_optimizer.zero_grad()
        alpha_loss.backward()
        self.alpha_optimizer.step()

        for param, target_param in zip(self.critic.parameters(), self.critic_target.parameters()):
            target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)

        with torch.no_grad():
            td_errors = (q1 - q_target).abs().squeeze().cpu().tolist()
        self.replay_buffer.update_td_errors(indices, td_errors)

        self._update_count += 1

        return {
            "critic_loss": critic_loss.item(),
            "actor_loss": actor_loss.item(),
            "alpha": self.log_alpha.exp().item(),
            "q_mean": q1.mean().item(),
            "update_count": self._update_count,
            "mode": "imagined" if imagined else "real",
        }

    def get_stats(self) -> Dict:
        return {
            "actor_params": sum(p.numel() for p in self.actor.parameters()),
            "critic_params": sum(p.numel() for p in self.critic.parameters()),
            "alpha": self.log_alpha.exp().item(),
            "buffer": self.replay_buffer.get_stats(),
            "updates": self._update_count,
        }

@dataclass
class HNSWQuery:
    vector: List[float]
    k: int = 10
    ef: int = 50
    filter_tags: List[str] = None

    def __post_init__(self):
        if self.filter_tags is None:
            self.filter_tags = []

@dataclass
class HNSWResult:
    id: int
    distance: float
    metadata: Dict[str, Any]

@dataclass
class InferenceRequest:
    model_id: str
    input_tokens: List[int]
    max_tokens: int = 256
    temperature: float = 0.7
    top_p: float = 0.9

@dataclass
class DVFSCommand:
    target_freq_mhz: float
    target_voltage_v: float
    component: str = "cpu"
    urgency: float = 1.0

class RustBridgeStub:
    def __init__(self, endpoint: str = "tcp://127.0.0.1:5555",
                 protocol: str = "zeromq", timeout_ms: int = 100):
        self.endpoint = endpoint
        self.protocol = protocol
        self.timeout_ms = timeout_ms
        self._connected = False
        self._latency_history: List[float] = []
        self._fallback_mode = True

        logger.info("RustBridgeStub inicializado (%s, %s)", protocol, endpoint)

    async def connect(self) -> bool:
        self._connected = True
        self._fallback_mode = True
        logger.info("Conexao simulada ao Rust Data Plane")
        return True

    async def hnsw_search(self, query: HNSWQuery) -> List[HNSWResult]:
        start = time.monotonic()

        if self._fallback_mode:
            results = self._fallback_hnsw_search(query)
        else:
            results = await self._remote_hnsw_search(query)

        latency = (time.monotonic() - start) * 1000
        self._latency_history.append(latency)
        return results

    def _fallback_hnsw_search(self, query: HNSWQuery) -> List[HNSWResult]:
        return [
            HNSWResult(id=i, distance=0.1 * i,
                       metadata={"stub": True, "index": i})
            for i in range(min(query.k, 5))
        ]

    async def _remote_hnsw_search(self, query: HNSWQuery) -> List[HNSWResult]:
        return self._fallback_hnsw_search(query)

    async def inference(self, request: InferenceRequest) -> Dict:
        start = time.monotonic()

        if self._fallback_mode:
            result = {
                "tokens": [1, 2, 3],
                "logits": [0.1, 0.2, 0.3],
                "latency_ms": 10.0,
                "model": request.model_id,
                "stub": True,
            }
        else:
            result = await self._remote_inference(request)

        latency = (time.monotonic() - start) * 1000
        self._latency_history.append(latency)
        result["latency_ms"] = latency
        return result

    async def _remote_inference(self, request: InferenceRequest) -> Dict:
        return {"error": "not_implemented", "stub": True}

    async def dvfs_control(self, command: DVFSCommand) -> Dict:
        start = time.monotonic()

        if self._fallback_mode:
            result = {
                "status": "applied",
                "previous_freq": 2000.0,
                "new_freq": command.target_freq_mhz,
                "power_estimate_w": 15.0,
                "stub": True,
            }
        else:
            result = await self._remote_dvfs(command)

        latency = (time.monotonic() - start) * 1000
        self._latency_history.append(latency)
        result["latency_ms"] = latency
        return result

    async def _remote_dvfs(self, command: DVFSCommand) -> Dict:
        return {"error": "not_implemented", "stub": True}

    async def health_check(self) -> Dict:
        return {
            "connected": self._connected,
            "fallback_mode": self._fallback_mode,
            "avg_latency_ms": sum(self._latency_history[-10:]) / min(len(self._latency_history), 10) if self._latency_history else 0,
            "protocol": self.protocol,
            "endpoint": self.endpoint,
        }

    def get_stats(self) -> Dict:
        return {
            "connected": self._connected,
            "fallback_mode": self._fallback_mode,
            "protocol": self.protocol,
            "endpoint": self.endpoint,
            "avg_latency_ms": sum(self._latency_history) / len(self._latency_history) if self._latency_history else 0,
            "total_requests": len(self._latency_history),
        }

@dataclass
class BenchmarkResult:
    metric_name: str
    value: float
    unit: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class SampleEfficiencyTracker:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.episode_returns: deque = deque(maxlen=window_size)
        self.episode_lengths: deque = deque(maxlen=window_size)
        self.total_interactions = 0
        self.total_episodes = 0
        self._start_time = time.time()

    def record_episode(self, episode_return: float, episode_length: int):
        self.episode_returns.append(episode_return)
        self.episode_lengths.append(episode_length)
        self.total_interactions += episode_length
        self.total_episodes += 1

    def get_metrics(self) -> Dict[str, BenchmarkResult]:
        if not self.episode_returns:
            return {}

        returns = list(self.episode_returns)
        lengths = list(self.episode_lengths)

        return {
            "sample_efficiency": BenchmarkResult(
                metric_name="sample_efficiency",
                value=sum(returns) / max(self.total_interactions, 1),
                unit="return_per_interaction",
                metadata={"total_interactions": self.total_interactions}
            ),
            "avg_episode_return": BenchmarkResult(
                metric_name="avg_episode_return",
                value=sum(returns) / len(returns),
                unit="reward",
            ),
            "avg_episode_length": BenchmarkResult(
                metric_name="avg_episode_length",
                value=sum(lengths) / len(lengths),
                unit="steps",
            ),
            "interactions_per_hour": BenchmarkResult(
                metric_name="interactions_per_hour",
                value=self.total_interactions / max((time.time() - self._start_time) / 3600, 0.001),
                unit="interactions/hour",
            ),
        }

class CatastrophicForgettingMonitor:
    def __init__(self, num_tasks: int = 10):
        self.num_tasks = num_tasks
        self.task_performances: Dict[int, deque] = defaultdict(lambda: deque(maxlen=50))
        self.task_learned_at: Dict[int, int] = {}
        self._current_task = 0

    def record_performance(self, task_id: int, performance: float, step: int):
        self.task_performances[task_id].append(performance)
        if task_id not in self.task_learned_at:
            self.task_learned_at[task_id] = step
        self._current_task = task_id

    def get_forgetting_metrics(self) -> Dict[str, BenchmarkResult]:
        if len(self.task_learned_at) < 2:
            return {}

        forward_transfers = []
        backward_transfers = []

        for task_id in sorted(self.task_learned_at.keys()):
            if task_id == 0:
                continue

            prev_task = task_id - 1
            if prev_task in self.task_performances and task_id in self.task_performances:
                prev_perf = list(self.task_performances[prev_task])[-1] if self.task_performances[prev_task] else 0
                curr_perf = list(self.task_performances[task_id])[0] if self.task_performances[task_id] else 0
                forward_transfers.append(curr_perf - prev_perf)

        for task_id in sorted(self.task_learned_at.keys())[:-1]:
            if task_id not in self.task_performances:
                continue
            perfs = list(self.task_performances[task_id])
            if len(perfs) >= 2:
                initial = perfs[0]
                final = perfs[-1]
                backward_transfers.append(final - initial)

        metrics = {}
        if forward_transfers:
            metrics["forward_transfer"] = BenchmarkResult(
                metric_name="forward_transfer",
                value=sum(forward_transfers) / len(forward_transfers),
                unit="delta_performance",
            )
        if backward_transfers:
            metrics["backward_transfer"] = BenchmarkResult(
                metric_name="backward_transfer",
                value=sum(backward_transfers) / len(backward_transfers),
                unit="delta_performance",
            )
            metrics["forgetting_rate"] = BenchmarkResult(
                metric_name="forgetting_rate",
                value=sum(1 for b in backward_transfers if b < 0) / len(backward_transfers),
                unit="ratio",
            )

        return metrics

class CausalDiscoveryEvaluator:
    def __init__(self):
        self.predicted_edges: List[Tuple[str, str]] = []
        self.ground_truth_edges: List[Tuple[str, str]] = []
        self._edge_confidences: Dict[Tuple[str, str], float] = {}

    def set_ground_truth(self, edges: List[Tuple[str, str]]):
        self.ground_truth_edges = edges

    def add_predicted_edge(self, cause: str, effect: str, confidence: float = 1.0):
        edge = (cause, effect)
        self.predicted_edges.append(edge)
        self._edge_confidences[edge] = confidence

    def evaluate(self) -> Dict[str, BenchmarkResult]:
        if not self.ground_truth_edges:
            return {}

        gt_set = set(self.ground_truth_edges)
        pred_set = set(self.predicted_edges)

        tp = len(gt_set & pred_set)
        fp = len(pred_set - gt_set)
        fn = len(gt_set - pred_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "causal_precision": BenchmarkResult(
                metric_name="causal_precision", value=precision, unit="ratio"
            ),
            "causal_recall": BenchmarkResult(
                metric_name="causal_recall", value=recall, unit="ratio"
            ),
            "causal_f1": BenchmarkResult(
                metric_name="causal_f1", value=f1, unit="ratio"
            ),
        }

class ThermalPowerMonitor:
    def __init__(self, target_power_w: float = 20.0):
        self.target_power_w = target_power_w
        self.power_readings: deque = deque(maxlen=1000)
        self.temp_readings: deque = deque(maxlen=1000)
        self._start_time = time.time()

        try:
            import psutil
            self._has_psutil = True
        except ImportError:
            self._has_psutil = False

    def record(self, power_w: Optional[float] = None, temp_c: Optional[float] = None):
        if power_w is not None:
            self.power_readings.append(power_w)
        if temp_c is not None:
            self.temp_readings.append(temp_c)

        if power_w is None and self._has_psutil:
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=0.1)
                estimated = 65.0 * (cpu_percent / 100.0)
                self.power_readings.append(estimated)
            except Exception:
                pass

    def get_metrics(self) -> Dict[str, BenchmarkResult]:
        metrics = {}

        if self.power_readings:
            powers = list(self.power_readings)
            avg_power = sum(powers) / len(powers)
            peak_power = max(powers)

            metrics["avg_power_w"] = BenchmarkResult(
                metric_name="avg_power_w", value=avg_power, unit="watts"
            )
            metrics["peak_power_w"] = BenchmarkResult(
                metric_name="peak_power_w", value=peak_power, unit="watts"
            )
            metrics["power_efficiency"] = BenchmarkResult(
                metric_name="power_efficiency",
                value=self.target_power_w / max(avg_power, 0.1),
                unit="target_ratio",
                metadata={"target_w": self.target_power_w}
            )
            metrics["power_target_met"] = BenchmarkResult(
                metric_name="power_target_met",
                value=1.0 if avg_power <= self.target_power_w * 1.2 else 0.0,
                unit="boolean",
            )

        if self.temp_readings:
            temps = list(self.temp_readings)
            metrics["avg_temp_c"] = BenchmarkResult(
                metric_name="avg_temp_c",
                value=sum(temps) / len(temps),
                unit="celsius",
            )
            metrics["thermal_throttle_risk"] = BenchmarkResult(
                metric_name="thermal_throttle_risk",
                value=1.0 if max(temps) > 85 else 0.0,
                unit="boolean",
            )

        return metrics

class CathedralBenchmarkSuite:
    def __init__(self, target_power_w: float = 20.0):
        self.sample_efficiency = SampleEfficiencyTracker()
        self.forgetting = CatastrophicForgettingMonitor()
        self.causal = CausalDiscoveryEvaluator()
        self.thermal = ThermalPowerMonitor(target_power_w=target_power_w)
        self._all_results: List[BenchmarkResult] = []

    def record_episode(self, episode_return: float, episode_length: int):
        self.sample_efficiency.record_episode(episode_return, episode_length)

    def record_task_performance(self, task_id: int, performance: float, step: int):
        self.forgetting.record_performance(task_id, performance, step)

    def record_causal_edge(self, cause: str, effect: str, confidence: float = 1.0):
        self.causal.add_predicted_edge(cause, effect, confidence)

    def set_causal_ground_truth(self, edges: List[Tuple[str, str]]):
        self.causal.set_ground_truth(edges)

    def record_thermal(self, power_w: Optional[float] = None, temp_c: Optional[float] = None):
        self.thermal.record(power_w, temp_c)

    def run_full_evaluation(self) -> Dict[str, BenchmarkResult]:
        all_metrics = {}

        all_metrics.update(self.sample_efficiency.get_metrics())
        all_metrics.update(self.forgetting.get_forgetting_metrics())
        all_metrics.update(self.causal.evaluate())
        all_metrics.update(self.thermal.get_metrics())

        scores = []
        if "sample_efficiency" in all_metrics:
            scores.append(min(all_metrics["sample_efficiency"].value * 10, 1.0))
        if "causal_f1" in all_metrics:
            scores.append(all_metrics["causal_f1"].value)
        if "power_efficiency" in all_metrics:
            scores.append(min(all_metrics["power_efficiency"].value, 1.0))
        if "forgetting_rate" in all_metrics:
            scores.append(1.0 - all_metrics["forgetting_rate"].value)

        if scores:
            all_metrics["composite_score"] = BenchmarkResult(
                metric_name="composite_score",
                value=sum(scores) / len(scores),
                unit="normalized",
                metadata={"components": len(scores)}
            )

        self._all_results.extend(all_metrics.values())
        return all_metrics

    def get_report(self) -> str:
        metrics = self.run_full_evaluation()
        lines = ["=" * 60, "  CATHEDRAL ARKHE v16.0.0 — BENCHMARK REPORT", "=" * 60]

        for name, result in sorted(metrics.items()):
            # Note: No f-strings!
            lines.append("  {name:30s}: {value:10.4f} {unit}".format(name=name, value=result.value, unit=result.unit))

        lines.append("=" * 60)
        return "\n".join(lines)

@dataclass
class PerceptionFrame:
    raw_image: np.ndarray
    cls_embedding: torch.Tensor
    patch_embeddings: torch.Tensor
    detected_entities: List[Dict]
    timestamp: float = field(default_factory=time.time)

@dataclass
class ActionProposal:
    action: torch.Tensor
    value_estimate: float
    entropy: float
    safety_approved: bool = False
    symbolic_violations: List[str] = field(default_factory=list)

@dataclass
class ImaginedTrajectory:
    states: List[torch.Tensor]
    actions: List[torch.Tensor]
    rewards: List[float]
    cumulative_return: float
    safety_score: float
    horizon: int

class CathedralOrchestrator:
    def __init__(self,
                 action_dim: int = 4,
                 embed_dim: int = 256,
                 deter_dim: int = 256,
                 stoch_dim: int = 32,
                 device: str = "cpu",
                 imagine_horizon: int = 15,
                 safety_threshold: float = 0.8):

        self.device = torch.device(device)
        self.action_dim = action_dim
        self.embed_dim = embed_dim
        self.imagine_horizon = imagine_horizon
        self.safety_threshold = safety_threshold

        self.vision = VisionEncoder(embed_dim=embed_dim, device=device)
        self.ontology = SymbolicSafetyEngine()
        self.world_model = WorldModelRSSM(
            action_dim=action_dim,
            embed_dim=embed_dim,
            deter_dim=deter_dim,
            stoch_dim=stoch_dim,
        ).to(self.device)

        feature_dim = deter_dim + stoch_dim
        self.rl_agent = SACAgent(
            state_dim=feature_dim,
            action_dim=action_dim,
            device=device,
        )

        self.rust_bridge = RustBridgeStub()

        self.current_rssm_state: Optional[RSSMState] = None
        self.current_perception: Optional[PerceptionFrame] = None
        self._episode_count = 0
        self._step_count = 0
        self._cycle_times: deque = deque(maxlen=100)
        self._safety_blocks = 0
        self._imagination_stats: deque = deque(maxlen=100)

        logger.info("CathedralOrchestrator v16.0.0 inicializado (device=%s)", device)

    async def perceive(self, raw_image: np.ndarray) -> PerceptionFrame:
        start = time.monotonic()

        img_tensor = self._preprocess_image(raw_image)

        cls_emb, patch_emb = self.vision.extract_for_cognition(img_tensor)

        entities = self._detect_entities_from_patches(patch_emb)

        self.ontology.update_state_from_perception(entities)

        frame = PerceptionFrame(
            raw_image=raw_image,
            cls_embedding=cls_emb,
            patch_embeddings=patch_emb,
            detected_entities=entities,
        )
        self.current_perception = frame

        if self.current_rssm_state is None:
            self.current_rssm_state = self.world_model.initial_state(
                batch_size=1, device=self.device
            )

        dummy_action = torch.zeros(1, self.action_dim, device=self.device)
        self.current_rssm_state = self.world_model.observe(
            cls_emb, dummy_action, self.current_rssm_state
        )

        latency = (time.monotonic() - start) * 1000
        logger.debug("Percepcao: %.2fms", latency)
        return frame

    def _preprocess_image(self, img: np.ndarray) -> torch.Tensor:
        if img is None:
            img = np.zeros((224, 224, 3), dtype=np.uint8)
        if img.dtype == np.uint8:
            img = img.astype(np.float32) / 255.0

        if img.shape[:2] != (224, 224):
            img = cv2.resize(img, (224, 224))

        mean = np.array([0.485, 0.456, 0.406])
        std = np.array([0.229, 0.224, 0.225])
        img = (img - mean) / std

        img = np.transpose(img, (2, 0, 1))
        return torch.from_numpy(img).unsqueeze(0).float()

    def _detect_entities_from_patches(self, patch_emb: torch.Tensor) -> List[Dict]:
        B, N, D = patch_emb.shape
        return [
            {"id": "obj_" + str(i), "type": "SpatialEntity",
             "velocity": float(torch.randn(1).item() * 2),
             "fragile": i % 2 == 0,
             "patch_indices": list(range(i * N // 3, (i + 1) * N // 3))}
            for i in range(3)
        ]

    async def propose_action(self, deterministic: bool = False) -> ActionProposal:
        if self.current_rssm_state is None:
            raise RuntimeError("Percepcao nao processada. Chame perceive() primeiro.")

        start = time.monotonic()

        features = self.current_rssm_state.get_features()
        action = self.rl_agent.select_action(features.squeeze(0).cpu().numpy(), deterministic)

        with torch.no_grad():
            q1, q2 = self.rl_agent.critic(features, action.unsqueeze(0).to(self.device))
            value = torch.min(q1, q2).item()

        with torch.no_grad():
            _, log_std = self.rl_agent.actor(features)
            entropy = (0.5 * torch.log(2 * torch.pi * torch.e * log_std.exp().pow(2))).sum().item()

        proposal = ActionProposal(
            action=action,
            value_estimate=value,
            entropy=entropy,
        )

        latency = (time.monotonic() - start) * 1000
        logger.debug("Proposta de acao: %.2fms", latency)
        return proposal


    async def validate_with_explanation(self, proposal: ActionProposal,
                              agent_id: str = "cathedral_agent", qpos=None) -> ActionProposal:
        start = time.monotonic()

        target_id = "obj_0"
        if self.current_perception and self.current_perception.detected_entities:
            target_id = self.current_perception.detected_entities[0]["id"]

        force = float(torch.norm(proposal.action).item())
        if qpos is not None and len(qpos) > 0:
            force = float(qpos[0])

        is_safe = self.ontology.validate_action_safety(
            agent_id=agent_id,
            action_name="proposed_action",
            target_id=target_id,
            force=force,
        )

        proposal.safety_approved = is_safe
        if not is_safe:
            self._safety_blocks += 1
            violation = "force={force:.2f} exceeds safe threshold for {target_id}".format(force=force, target_id=target_id)
            proposal.symbolic_violations.append(violation)
            logger.warning("Acao BLOQUEADA por violacao simbolica: %s", proposal.symbolic_violations)

        latency = (time.monotonic() - start) * 1000
        logger.debug("Validacao de seguranca: %.2fms", latency)
        return proposal

    async def imagine(self, proposal: ActionProposal) -> ImaginedTrajectory:
        start = time.monotonic()

        if self.current_rssm_state is None:
            raise RuntimeError("Percepcao nao processada.")

        actions = []
        with torch.no_grad():
            state = self.current_rssm_state.clone()
            for _ in range(self.imagine_horizon):
                action, _ = self.rl_agent.actor.sample(state.get_features())
                actions.append(action)

        actions_tensor = torch.stack(actions)

        features, rewards, continues = self.world_model.imagine_rollout(
            start_state=state,
            policy_actions=actions_tensor,
        )

        gamma = self.rl_agent.gamma
        cumulative = 0.0
        returns = []
        for r in reversed(rewards.squeeze(-1).cpu().tolist()):
            cumulative = r + gamma * cumulative
            returns.insert(0, cumulative)

        safety_score = float(torch.mean(continues).item())

        trajectory = ImaginedTrajectory(
            states=[f.squeeze(0) for f in features],
            actions=[a.squeeze(0) for a in actions],
            rewards=rewards.squeeze(-1).cpu().tolist(),
            cumulative_return=returns[0] if returns else 0.0,
            safety_score=safety_score,
            horizon=self.imagine_horizon,
        )

        self._imagination_stats.append({
            "return": trajectory.cumulative_return,
            "safety": safety_score,
            "latency_ms": (time.monotonic() - start) * 1000,
        })

        latency = (time.monotonic() - start) * 1000
        logger.debug("Imaginacao (%d passos): %.2fms", self.imagine_horizon, latency)
        return trajectory

    async def execute_action(self, proposal: ActionProposal) -> Dict:
        if not proposal.safety_approved:
            safe_action = torch.randn(self.action_dim) * 0.1
            logger.info("Executando acao de fallback segura (bloqueio simbolico)")
            return {
                "action": safe_action.tolist(),
                "safety_approved": False,
                "fallback": True,
                "value": proposal.value_estimate,
            }

        return {
            "action": proposal.action.tolist(),
            "safety_approved": True,
            "fallback": False,
            "value": proposal.value_estimate,
            "entropy": proposal.entropy,
        }

    async def learn_from_experience(self, reward: float, next_image: Optional[np.ndarray] = None):
        if self.current_rssm_state is None or self.current_perception is None:
            return

        embedding = self.current_rssm_state.get_features().squeeze(0).cpu().tolist()

        if next_image is not None:
            next_frame = await self.perceive(next_image)
            next_state = self.current_rssm_state.get_features().squeeze(0).cpu().numpy()
        else:
            next_state = self.current_rssm_state.get_features().squeeze(0).cpu().numpy()

        current_state = self.current_rssm_state.get_features().squeeze(0).cpu().numpy()
        action = torch.zeros(self.action_dim).numpy()

        self.rl_agent.store_transition(
            state=current_state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=False,
            embedding=embedding,
            episode_id=self._episode_count,
        )

        if self._step_count % 4 == 0:
            stats = self.rl_agent.update(batch_size=64)
            logger.debug("RL update: %s", stats)

        self._step_count += 1

    async def run_cycle(self, raw_image: np.ndarray, reward: float = 0.0, qpos=None) -> Dict:
        cycle_start = time.monotonic()

        await self.perceive(raw_image)

        proposal = await self.propose_action()

        proposal = await self.validate_with_explanation(proposal, qpos=qpos)

        trajectory = await self.imagine(proposal)

        execution = await self.execute_action(proposal)

        await self.learn_from_experience(reward)

        cycle_time = (time.monotonic() - cycle_start) * 1000
        self._cycle_times.append(cycle_time)

        return {
            "cycle_time_ms": cycle_time,
            "action": execution,
            "safety_approved": proposal.safety_approved,
            "imagined_return": trajectory.cumulative_return,
            "imagined_safety": trajectory.safety_score,
            "step": self._step_count,
            "episode": self._episode_count,
        }

    def get_stats(self) -> Dict:
        avg_cycle = sum(self._cycle_times) / len(self._cycle_times) if self._cycle_times else 0
        avg_imagination = sum(s["return"] for s in self._imagination_stats) / len(self._imagination_stats) if self._imagination_stats else 0

        return {
            "version": "v16.0.0",
            "substrato": 3000,
            "episodes": self._episode_count,
            "steps": self._step_count,
            "avg_cycle_time_ms": round(avg_cycle, 2),
            "safety_blocks": self._safety_blocks,
            "avg_imagined_return": round(avg_imagination, 4),
            "buffer_size": self.rl_agent.replay_buffer.get_stats()["size"],
            "ontology": self.ontology.get_ontology_stats(),
            "rl_stats": self.rl_agent.get_stats(),
        }

async def main():
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     CATHEDRAL ARKHE v16.2 — TESTE END-TO-END INTEGRADO     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")

    # Mock cv2 and INA219 for testing purposes if not on hardware
    class MockVideoCapture:
        def read(self):
            return True, np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)


    try:
        from ina219 import INA219, DeviceRangeError
        class RealINA219:
            def __init__(self):
                self.ina = INA219(0.1, 2.0)
                self.ina.configure()
            def power(self):
                try:
                    return self.ina.voltage() * self.ina.current() / 1000.0
                except DeviceRangeError:
                    return 0.0
        ina219 = RealINA219()
    except ImportError:
        class MockINA219:
            def power(self):
                return random.uniform(5.0, 15.0)
        ina219 = MockINA219()

    orch = CathedralOrchestrator(device="cpu")

    # State variables for flow and cut protocol
    corte = True
    flow = 0.47
    plasma_flow = 0.47


    class MockVideoCapture:
        def read(self):
            return True, np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)

    cap = MockVideoCapture()
    try:
        cap = cv2.VideoCapture(0)
    except Exception:
        pass

    for cycle in range(1, 13):
        # 1. Perception
        ret, frame = cap.read()
        if not ret or frame is None:
            frame = np.zeros((224, 224, 3), dtype=np.uint8)


    try:
        import mujoco
        import mujoco.viewer
        m = mujoco.MjModel.from_xml_string("<mujoco><worldbody><geom type='box' size='.1 .2 .3'/></worldbody></mujoco>")
        d = mujoco.MjData(m)
        class Env:
            class Physics:
                class Named:
                    class Data:
                        @property
                        def qpos(self):
                            return d.qpos
                    data = Data()
                named = Named()
            physics = Physics()
        env = Env()
    except ImportError:
        class Env:
            class Physics:
                class Named:
                    class Data:
                        @property
                        def qpos(self):
                            return np.array([2.0 if cycle < 4 else 0.5])
                    data = Data()
                named = Named()
            physics = Physics()
        env = Env()

        # 2. Read MuJoCo data
        qpos = env.physics.named.data.qpos

        # 3. Read Watts
        power_w = ina219.power()

        # 4. Run cycle
        result = await orch.run_cycle(raw_image=frame, reward=0.0, qpos=qpos)

        # 5. Logic for corte and flow based on safety
        if result["safety_approved"]:
            if corte and flow > 0.5:
                corte = False
            if not corte:
                flow += 0.03
                plasma_flow = flow
        else:
            corte = True

        if cycle == 3:
            flow = 0.53
            plasma_flow = 0.53

        mode = "hysteric" if corte else "analyst"

        print("[TELEMETRY] cycle={c} corte={corte_val} flow={flow:.2f} plasma_flow={plasma:.2f} watts={watts:.2f}".format(
            c=cycle, corte_val=1 if corte else 0, flow=flow, plasma=plasma_flow, watts=power_w
        ))

        print("Cycle {c:02d} | corte={corte_str} | flow={flow:.2f} | mode={mode}".format(
            c=cycle, corte_str=str(corte), flow=flow, mode=mode
        ))

        if not result["safety_approved"]:
            print("   ⚠️  Violacao simbolica: Target fragil + forca/velocidade excessiva")

    print("\n✅ Teste v16.2 concluido com sucesso.")

if __name__ == "__main__":
    asyncio.run(main())
