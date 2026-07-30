"""
Coleta de dados de interação para fine-tuning via NexRL.
"""
import json
import time
import logging
from pathlib import Path
logger = logging.getLogger("cathedral.nexrl_bridge")

class InteractionLogger:
    """Loga interações para dataset de fine-tuning DPO/PPO."""

    def __init__(self, data_dir="zvec_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = self.data_dir / "interactions_{0}.jsonl".format(int(time.time()))
        self._count = 0

    def log_interaction(self, observation, fast_action, slow_decision, reward, route):
        """Registra uma interação completa."""
        entry = {
            "timestamp": time.time(),
            "observation_summary": str(observation)[:200] if observation else None,
            "fast_brain_action": list(fast_action) if hasattr(fast_action, 'tolist') else list(fast_action),
            "slow_brain_decision": slow_decision,
            "reward": float(reward),
            "route": route,  # "fast" ou "slow"
            "safety_approved": slow_decision.get("safety_override", False),
        }

        with open(self.current_file, "a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self._count += 1
        if self._count % 100 == 0:
            logger.info("NexRL: {0} interações logadas".format(self._count))

    def train(self, config_path=None):
        """Inicia fine-tuning via NexRL."""
        try:
            import nexrl
            if config_path is None:
                config_path = str(self.data_dir / "nexrl_config.yaml")
            nexrl.train(config=config_path, data=str(self.current_file))
        except ImportError:
            logger.warning("NexRL não disponível para treinamento")
