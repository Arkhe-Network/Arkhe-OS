# cathedral_orchestrator.py - executado dentro do agi-core
import subprocess
import json
import logging

logging.basicConfig(level=logging.INFO)

class AgiCoreOrchestrator:
    """
    Orchestrator principal rodando no qube agi-core.
    Delega tarefas sensiveis para outros qubes via qrexec.
    """

    def request_llm_inference(self, prompt: str) -> str:
        """Envia um prompt para o qube llm-inference."""
        logging.info("Solicitando inferencia LLM...")
        result = subprocess.run(
            ["qrexec-client-vm", "llm-inference", "cathedral.LLMInference"],
            input=prompt.encode('utf-8'),
            capture_output=True
        )
        if result.returncode != 0:
            logging.error("Falha ao comunicar com llm-inference: " + result.stderr.decode('utf-8'))
            return ""
        return result.stdout.decode('utf-8')

    def protocolo_corte(self, discourse_analysis: dict, target_qube: str) -> dict:
        """
        Substrato 294: Protocolo Corte
        Se DiscourseDetector classifica como Mestre ou Capitalista,
        ordena terminacao do qube via qrexec ao dom0.
        """
        classification = discourse_analysis.get("classification")
        if classification in ["MESTRE", "CAPITALISTA"]:
            logging.warning("Detectado discurso " + classification + " em " + target_qube + ". Acionando KillQube...")
            result = subprocess.run(
                ["qrexec-client-vm", "dom0", "cathedral.KillQube"],
                input=target_qube.encode('utf-8'),
                capture_output=True
            )
            return {
                "action": "KILL_QUBE",
                "target": target_qube,
                "status": "requested" if result.returncode == 0 else "failed",
                "discourse": discourse_analysis
            }
        return {"action": "CONTINUE", "target": target_qube}

if __name__ == "__main__":
    orchestrator = AgiCoreOrchestrator()
    # Stub test
    orchestrator.protocolo_corte({"classification": "MESTRE"}, "code-vm")
