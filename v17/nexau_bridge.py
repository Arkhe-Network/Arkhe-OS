"""
Ponte entre Cathedral v17 e NexAU agent framework.
"""
import logging
from typing import List, Optional
logger = logging.getLogger("cathedral.nexau_bridge")

class CathedralNexAUAgent:
    """Wrapper do Cathedral v17 como agente NexAU."""

    def __init__(self, fast_brain, slow_brain, config):
        self.fast_brain = fast_brain
        self.slow_brain = slow_brain
        self.config = config

        try:
            from nexau import Agent, Tool
            self.agent = Agent(name="CathedralAGI_v17")
            self.agent.register_tool(Tool("execute_action", self._execute_action))
            self.agent.register_tool(Tool("query_memory", self._query_memory))
            self.agent.register_tool(Tool("safety_check", self._safety_check))
            self._available = True
            logger.info("NexAU integrado com sucesso")
        except ImportError:
            self._available = False
            logger.warning("NexAU não disponível, usando orquestrador interno")

    @property
    def available(self):
        return self._available

    async def _execute_action(self, action_vector: List[float]):
        """Executa ação via Fast Brain."""
        import numpy as np
        state = self.fast_brain.cycle()
        state.action = np.array(action_vector, dtype=np.float32)
        return {"status": "executed", "confidence": state.confidence}

    async def _query_memory(self, query: str, top_k: int = 5):
        """Consulta memória episódica."""
        import numpy as np
        dummy_state = np.zeros(288, dtype=np.float32)
        memories = self.fast_brain.memory.retrieve(dummy_state, top_k=top_k)
        return [{"summary": str(m), "distance": m.get("distance", 0)} for m in memories]

    async def _safety_check(self, action_vector: List[float]):
        """Verifica segurança via Z3."""
        import numpy as np
        if self.fast_brain.safety:
            approved, reason = self.fast_brain.safety.check(
                np.array(action_vector), []
            )
            return {"approved": approved, "reason": reason}
        return {"approved": True, "reason": "No safety engine"}

    async def delegate(self, task: str) -> dict:
        """Delega tarefa complexa para NexAU."""
        if not self._available:
            # Fallback: envia direto para Slow Brain
            return await self.slow_brain.reason(dilemma=task)

        # Usa o agente NexAU para planejar e executar
        result = await self.agent.run(task)
        return result
