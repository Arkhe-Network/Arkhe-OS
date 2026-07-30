import math
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)

class ReasoningMode:
    Explicit = 0
    Latent = 1

class CognitiveDirective:
    Proceed = 0
    TerminateEarly = 1

class SwireResult:
    def __init__(self, mode, directive, should_force_terminate, current_entropy_x1000):
        self.mode = mode
        self.directive = directive
        self.should_force_terminate = should_force_terminate
        self.current_entropy_x1000 = current_entropy_x1000

class ProtocoloCorte:
    def __init__(self):
        self.state = 0 # 0 = Normal, 2 = Corte Ativo

class PlasmaMetrics:
    def __init__(self):
        self.temperature = 1.0
        self.flow_intensity = 1.0
        self.plasma_density = 1.0

class Plasma:
    def __init__(self):
        self.metrics = PlasmaMetrics()

class SwireConfig:
    def __init__(self):
        self.entropy_ref_x1000 = 4500
        self.dwell_e2l_steps = 512
        self.max_switches = 3
        self.alpha_0_x1000 = 700
        self.beta_0_x1000 = 700

class SwireasoningEngine:
    def __init__(self, config=None):
        if config is None:
            config = SwireConfig()
        self.config = config
        self.current_mode = ReasoningMode.Explicit
        self.switch_count = 0
        self.dwell_counter = 0
        self.block_entropy_ref_x1000 = config.entropy_ref_x1000

    def evaluate_step(self, logits: List[float], current_token: int, corte_state: int) -> SwireResult:
        if corte_state == 2:
            return SwireResult(
                mode=ReasoningMode.Explicit,
                directive=CognitiveDirective.Proceed,
                should_force_terminate=False,
                current_entropy_x1000=0
            )

        current_entropy = self.calculate_shannon_x1000(logits)

        next_mode = self.current_mode
        if self.current_mode == ReasoningMode.Explicit:
            if current_entropy > self.block_entropy_ref_x1000 and self.dwell_counter >= self.config.dwell_e2l_steps:
                self._execute_switch(ReasoningMode.Latent)
                next_mode = ReasoningMode.Latent
        elif self.current_mode == ReasoningMode.Latent:
            if current_entropy < self.block_entropy_ref_x1000:
                self._execute_switch(ReasoningMode.Explicit)
                next_mode = ReasoningMode.Explicit

        should_terminate = self.switch_count >= self.config.max_switches

        return SwireResult(
            mode=next_mode,
            directive=CognitiveDirective.Proceed,
            should_force_terminate=should_terminate,
            current_entropy_x1000=current_entropy
        )

    def _execute_switch(self, new_mode: int):
        if new_mode != self.current_mode:
            self.current_mode = new_mode
            self.switch_count += 1
            self.dwell_counter = 0
            self.block_entropy_ref_x1000 = 0
        else:
            self.dwell_counter += 1

    @staticmethod
    def calculate_shannon_x1000(logits: List[float]) -> int:
        if not logits:
            return 10000
        max_logit = max(logits)
        sum_exp = sum(math.exp(logit - max_logit) for logit in logits)
        if sum_exp == 0.0:
            return 10000
        log_entropy = -((math.log(sum_exp)) / len(logits))
        return int(log_entropy * 1000.0)

class ArkheAsiV12:
    def __init__(self):
        self.protocolo_corte = ProtocoloCorte()
        self.plasma = Plasma()
        self.swire_engine = SwireasoningEngine()

    def _calculate_entropy_python(self, logits: List[float]) -> int:
         return SwireasoningEngine.calculate_shannon_x1000(logits)

    def cycle_swireasoning(self, logits: List[float], current_token_id: int) -> Dict[str, Any]:
        if getattr(self, 'swire_engine', None):
            swire_result = self.swire_engine.evaluate_step(
                logits=logits,
                current_token=current_token_id,
                corte_state=self.protocolo_corte.state
            )
        else:
            current_entropy = self._calculate_entropy_python(logits)
            swire_result = SwireResult(
                mode=ReasoningMode.Explicit,
                directive=CognitiveDirective.Proceed,
                should_force_terminate=False,
                current_entropy_x1000=current_entropy
            )

        if swire_result.mode == ReasoningMode.Latent:
            self.plasma.metrics.temperature += 0.15
            self.plasma.metrics.flow_intensity *= 0.6

        if swire_result.mode == ReasoningMode.Explicit:
            self.plasma.metrics.flow_intensity = min(1.2, self.plasma.metrics.flow_intensity + 0.4)
            self.plasma.metrics.plasma_density *= 0.9

        if swire_result.should_force_terminate:
            logging.warning("[SWIRE] Max switches atingido. Forcando convergencia prematura.")
            return {
                "directive": "TERMINATE_EARLY",
                "reason": "Max switches atingido. Emitindo resposta com raciocinio parcial.",
                "plasma_temp": round(self.plasma.metrics.temperature, 3),
                "swire_mode": "Explicit (Termination)"
            }

        return {
            "directive": "PROCEED",
            "swire_mode": "Latent" if swire_result.mode == ReasoningMode.Latent else "Explicit",
            "entropy_x1000": swire_result.current_entropy_x1000,
            "switches_remaining": self.swire_engine.config.max_switches - self.swire_engine.switch_count
        }

if __name__ == "__main__":
    orchestrator = ArkheAsiV12()
    print(orchestrator.cycle_swireasoning([1.0, 2.0, 3.0, 4.0], 10))
