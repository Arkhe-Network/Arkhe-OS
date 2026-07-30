#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral ARKHE — PicoAds Tool for LLM Agents
Selo: CATHEDRAL-ARKHE-PICOADS-TOOL-2026-06-16

Permite que o agente solicite recomendações de anúncios via driver kernel PicoAds
ou diretamente pela API HTTP (fallback). Suporta atestação de memória e trust tier.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional
import httpx
try:
    import win32file  # opcional, para named pipe no Windows
except ImportError:
    win32file = None
from dataclasses import dataclass

from agent.tools.base import BaseTool, ToolResult

@dataclass
class PicoAdsTool(BaseTool):
    _description: str = "Obtém recomendações personalizadas de anúncios/produtos baseadas no contexto do usuário."
    _name: str = "picoads"

    # Configuração
    use_kernel_driver: bool = True   # se False, usa HTTP API
    pipe_name: str = r"\\.\pipe\PicoAdsService"
    api_base: str = os.getenv("PICOADS_API_BASE", "https://api.picoads.cathedral.io/v1")
    api_key: str = os.getenv("PICOADS_API_KEY", "")
    trust_tier: int = 200            # 0-255, 200+ requer prova de memória
    memory_proof_required: bool = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    async def run(self, **kwargs) -> ToolResult:
        """
        kwargs deve conter:
          - user_context_hash: str (hash Blake3 do contexto do usuário)
          - max_results: int (opcional, default 3)
        Retorna lista de recomendações.
        """
        user_context_hash = kwargs.get("user_context_hash")
        if not user_context_hash:
            return ToolResult(success=False, error="Missing 'user_context_hash' in kwargs")

        max_results = kwargs.get("max_results", 3)

        if self.use_kernel_driver and win32file is not None:
            res = await self._call_kernel_driver(user_context_hash, max_results)
        else:
            res = await self._call_http_api(user_context_hash, max_results)

        if "error" in res and res["error"]:
            return ToolResult(success=False, error=res["error"])
        return ToolResult(success=True, data=res)

    async def _call_kernel_driver(self, ctx_hash: str, max_results: int) -> Dict:
        """Comunica-se com o driver kernel via named pipe."""
        try:
            # Abrir o pipe nomeado
            handle = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )
            # Construir requisição no formato esperado pelo driver (JSON simples)
            request = {
                "user_context_hash": ctx_hash,
                "max_results": max_results,
                "trust_tier": self.trust_tier,
                "memory_proof_required": self.memory_proof_required,
                "cathedral_version": "28.1"
            }
            request_json = json.dumps(request).encode('utf-8')
            win32file.WriteFile(handle, request_json)

            # Ler resposta (tamanho fixo 4096 bytes)
            _, response_data = win32file.ReadFile(handle, 4096)
            win32file.CloseHandle(handle)

            response = json.loads(response_data.decode('utf-8'))
            return response
        except Exception as e:
            return {"error": "Kernel driver communication failed: {error}".format(error=str(e)), "recommendations": []}

    async def _call_http_api(self, ctx_hash: str, max_results: int) -> Dict:
        """Fallback: chamada HTTP direta para a API PicoAds."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    "{base}/recommendations".format(base=self.api_base),
                    headers={"X-API-Key": self.api_key},
                    params={
                        "context_hash": ctx_hash,
                        "limit": max_results,
                        "trust_tier": self.trust_tier
                    }
                )
                resp.raise_for_status()
                recs = resp.json()
                return {"recommendations": recs, "status": "success"}
            except Exception as e:
                return {"error": str(e), "recommendations": []}
