"""
Cathedral ARKHE v17.0 - Orquestrador Principal
Coordena Fast Brain, Slow Brain, Router, e Memória.
"""
import asyncio
import time
import logging
import numpy as np
from typing import Optional
from dataclasses import dataclass, field

from .fast_brain import FastBrain, FastBrainState
from .slow_brain import SlowBrainSGLang
from .config_loader import CathedralConfig

logger = logging.getLogger("cathedral.orchestrator")


@dataclass
class OrchestratorResult:
    action: np.ndarray
    confidence: float
    route: str              # "fast" ou "slow"
    safety_approved: bool
    slow_brain_reasoning: str = ""
    latency_ms: float = 0.0
    fast_brain_state: Optional[FastBrainState] = None


class Router:
    """Decide se usa Fast ou Slow Brain."""

    def __init__(self, config):
        self.config = config.router
        self.confidence_threshold = self.config["confidence_threshold"]
        self.deadlock_window = self.config["deadlock_window"]
        self.deadlock_threshold = self.config["deadlock_threshold"]
        self._action_history = []

    def decide(
        self,
        fast_state: FastBrainState,
        slow_available: bool = True,
    ) -> str:
        """Retorna 'fast' ou 'slow'."""
        rules = self.config.get("rules", [])

        # Ordena por prioridade (menor = mais importante)
        rules_sorted = sorted(rules, key=lambda r: r["priority"])

        for rule in rules_sorted:
            if self._evaluate_rule(rule, fast_state, slow_available):
                action = rule["action"]
                logger.debug("Router: {0} -> {1}".format(rule['name'], action))
                return action.replace("route_to_", "")  # "fast" ou "slow"

        return "fast"

    def _evaluate_rule(self, rule, fast_state, slow_available):
        cond = rule["condition"]

        if cond == "not safety_approved":
            return not fast_state.safety_approved

        if cond.startswith("confidence < "):
            threshold = float(cond.split("<")[-1].strip())
            return fast_state.confidence < threshold

        if "action_variance" in cond and "over" in cond:
            self._action_history.append(fast_state.action.copy())
            if len(self._action_history) > self.deadlock_window:
                self._action_history = self._action_history[-self.deadlock_window:]
            if len(self._action_history) >= self.deadlock_window:
                variance = float(np.var(np.array(self._action_history)))
                return variance < self.deadlock_threshold

        if "zvec_memory_count == 0" in cond:
            return len(fast_state.zvec_memories) == 0

        if cond == "default":
            return True

        return False


class CathedralAGI_v17:
    """Orquestrador principal do Cathedral ARKHE v17.0."""

    def __init__(self, config_path=None):
        self.config = CathedralConfig(config_path)
        self.router = Router(self.config)

        # Fast Brain (sempre local)
        self.fast_brain = FastBrain(self.config)

        # Slow Brain (SGLang, pode estar offline)
        self.slow_brain = SlowBrainSGLang(self.config)
        self._slow_healthy = False

        # NexAU (opcional)
        self.nexau = None
        try:
            from .nexau_bridge import CathedralNexAUAgent
            self.nexau = CathedralNexAUAgent(self.fast_brain, self.slow_brain, self.config)
            if not self.nexau.available:
                self.nexau = None
        except ImportError:
            pass

        # NexRL logger (opcional)
        self.nexrl_logger = None
        try:
            from .nexrl_bridge import InteractionLogger
            self.nexrl_logger = InteractionLogger()
        except ImportError:
            pass

        logger.info("Cathedral AGI v{0} inicializado".format(self.config._config['cathedral']['version']))

    async def health_check(self):
        """Verifica saúde de todos os componentes."""
        self._slow_healthy = await self.slow_brain.health_check()
        return {
            "fast_brain": True,
            "slow_brain": self._slow_healthy,
            "nexau": self.nexau is not None and self.nexau.available,
            "nexrl": self.nexrl_logger is not None,
        }

    async def cycle(self, observation=None) -> OrchestratorResult:
        """Executa um ciclo completo do Cathedral AGI."""
        t0 = time.perf_counter()

        # 1. Fast Brain cycle (sempre executa)
        fast_state = self.fast_brain.cycle(observation)

        # 2. Router decision
        route = self.router.decide(fast_state, slow_available=self._slow_healthy)

        # 3. Se route=slow e Slow Brain disponível, consulta
        if route == "slow" and self._slow_healthy:
            # Se NexAU disponível, delega para ele
            if self.nexau:
                slow_result = await self.nexau.delegate(
                    "Observação: {0}\n"
                    "Fast Brain ação: {1}\n"
                    "Fast Brain confiança: {2:.3f}\n"
                    "Segurança aprovada: {3}\n"
                    "Memórias: {4} encontradas".format(
                        str(observation)[:200] if observation is not None else 'Nenhuma',
                        fast_state.action.tolist(),
                        fast_state.confidence,
                        fast_state.safety_approved,
                        len(fast_state.zvec_memories)
                    )
                )
            else:
                slow_result = await self.slow_brain.reason(
                    dilemma="Fast Brain propôs ação {0} com confiança {1:.3f}. Segurança: {2}. Memórias: {3} encontradas.".format(
                        fast_state.action.tolist(),
                        fast_state.confidence,
                        'aprovada' if fast_state.safety_approved else 'REJEITADA',
                        len(fast_state.zvec_memories)
                    ),
                    context=str(observation)[:500] if observation is not None else "",
                    memories=fast_state.zvec_memories,
                )

            action = np.array(slow_result["action_vector"], dtype=np.float32)
            confidence = slow_result["confidence"]
            reasoning = slow_result.get("reasoning", "")
            safety = slow_result.get("safety_override", False)
        else:
            # Usa decisão do Fast Brain
            action = fast_state.action
            confidence = fast_state.confidence
            reasoning = ""
            safety = fast_state.safety_approved

        # 4. Log para NexRL
        if self.nexrl_logger:
            self.nexrl_logger.log_interaction(
                observation=observation,
                fast_action=fast_state.action,
                slow_decision={"action_vector": action.tolist(), "confidence": confidence},
                reward=confidence,  # reward simplificado
                route=route,
            )

        latency = (time.perf_counter() - t0) * 1000

        return OrchestratorResult(
            action=action,
            confidence=confidence,
            route=route,
            safety_approved=safety,
            slow_brain_reasoning=reasoning,
            latency_ms=latency,
            fast_brain_state=fast_state,
        )

    async def run_loop(self, cycles=10, delay=0.01):
        """Loop principal para teste."""
        health = await self.health_check()
        print("Health: {0}".format(health))

        for i in range(cycles):
            result = await self.cycle()
            print("Cycle {0}: route={1}, conf={2:.3f}, action={3}, latency={4:.1f}ms".format(
                i+1, result.route, result.confidence,
                ["{0:.2f}".format(v) for v in result.action],
                result.latency_ms
            ))
            await asyncio.sleep(delay)


# Para execução direta
if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    agi = CathedralAGI_v17()
    asyncio.run(agi.run_loop(cycles=5))
