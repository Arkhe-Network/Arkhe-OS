#!/usr/bin/env python3
# pipeline_orchestrator.py – Orquestra LLM + MLIR Pass Manager

import subprocess
import json
import asyncio
from pathlib import Path
from typing import List, Dict
import httpx

from integrations.vllm_client import VLLMClient
from integrations.artifact_anchor.anchor import AnchorArtifact

class PipelineOrchestrator:
    def __init__(self, llm: VLLMClient, temporal_client):
        self.llm = llm
        self.temporal = temporal_client
        self.pass_manager = PassManagerBridge()

    async def suggest_and_run(self, mlir_file: Path, target: str = "c") -> Dict:
        # 1. LLM sugere pipeline de passes
        prompt = f"""
        Dado o arquivo MLIR com dialeto arkhe ({mlir_file.name}), sugira uma sequência de passes
        para gerar código {target} otimizado e verificado.
        Considere: lower‑to‑C, verify‑lean, generate‑hardware, optimize‑gpu.
        """
        llm_response = await self.llm.generate(prompt)
        passes = self._parse_passes(llm_response["text"])
        print(f"🧠 Pipeline sugerido: {passes}")

        # 2. Executa passes via MLIR
        result = self.pass_manager.run(mlir_file, passes, target)

        # 3. Ancora artefato
        anchor = AnchorArtifact(self.temporal)
        seal = anchor.anchor(mlir_file, result["output_file"], passes)

        return {
            "passes": passes,
            "output_file": result["output_file"],
            "phi_c": result.get("phi_c", 0.99),
            "seal": seal
        }

    def _parse_passes(self, text: str) -> List[str]:
        # Extrai lista de passes do texto gerado pelo LLM
        # Exemplo simplificado: procura por palavras‑chave
        possible = ["arkhe.lower-to-c", "arkhe.verify-lean", "arkhe.generate-geometry", "arkhe.optimize-gpu"]
        found = [p for p in possible if p in text]
        return found if found else ["arkhe.lower-to-c"]

class PassManagerBridge:
    """Ponte entre Python e o MLIR Pass Manager via subprocess."""
    def run(self, mlir_file: Path, passes: List[str], target: str) -> Dict:
        cmd = ["mlir-opt", str(mlir_file)]
        for p in passes:
            cmd.append(f"--{p}")
        if target == "c":
            cmd.append("--convert-to-c")
        elif target == "vhdl":
            cmd.append("--convert-to-vhdl")
        elif target == "gcode":
            cmd.append("--convert-to-gcode")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"MLIR pass failed: {result.stderr}")

        output_file = mlir_file.with_suffix(f".{target}")
        output_file.write_text(result.stdout)

        return {"output_file": output_file, "phi_c": 0.99}
