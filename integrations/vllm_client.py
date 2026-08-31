#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ARKHE OS — vLLM LOCAL CLIENT
================================================================================
Cliente HTTP para servidores vLLM locais com API compatível com OpenAI.
Suporta:
  - Llama 4 / Qwen 4 / Mistral Large
  - Inferência com temperatura, top_p, max_tokens
  - Streaming (opcional)
  - Integração com TemporalChain e Φ_C validation
================================================================================
"""

import os
import json
import time
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
import httpx
import asyncio

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================
DEFAULT_VLLM_URL = os.environ.get("VLLM_API_URL", "http://localhost:8000/v1")
DEFAULT_MODEL = os.environ.get("VLLM_MODEL", "meta-llama/Llama-4-70B-Instruct")
DEFAULT_API_KEY = os.environ.get("VLLM_API_KEY", "dummy-key")

# =============================================================================
# CLIENTE
# =============================================================================
class VLLMClient:
    """
    Cliente para servidor vLLM local (API OpenAI-compatible).
    """

    def __init__(
        self,
        base_url: str = DEFAULT_VLLM_URL,
        model: str = DEFAULT_MODEL,
        api_key: str = DEFAULT_API_KEY,
        timeout: float = 120.0,
        temporal_chain: Optional[Any] = None,
        phi_bus: Optional[Any] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.temporal = temporal_chain
        self.phi_bus = phi_bus
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()

    # -------------------------------------------------------------------------
    # INFERÊNCIA
    # -------------------------------------------------------------------------
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = 4096,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        seed: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Gera texto a partir de um prompt usando o modelo vLLM.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "stream": stream,
            "seed": seed,
        }
        if stop:
            payload["stop"] = stop
        payload.update(kwargs)

        start_time = time.time()
        try:
            if stream:
                # Streaming: retorna um gerador assíncrono
                return await self._stream_generate(payload)

            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            elapsed = time.time() - start_time

            result = {
                "text": data["choices"][0]["message"]["content"],
                "finish_reason": data["choices"][0].get("finish_reason"),
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model),
                "latency_seconds": elapsed,
                "phi_c": self._compute_phi_c(data, elapsed),
            }

            # Ancorar na TemporalChain
            if self.temporal:
                try:
                    seal = await self.temporal.anchor_event(
                        "vllm_inference",
                        {
                            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest(),
                            "response_hash": hashlib.sha256(result["text"].encode()).hexdigest(),
                            "model": self.model,
                            "phi_c": result["phi_c"],
                            "latency": elapsed
                        }
                    )
                    result["temporal_seal"] = seal
                except Exception as e:
                    logger.warning(f"Falha ao ancorar: {e}")

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erro na inferência: {e}")
            raise

    async def _stream_generate(self, payload: Dict) -> AsyncGenerator[str, None]:
        """Streaming de tokens."""
        async with self._client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    # -------------------------------------------------------------------------
    # MÉTRICAS DE COERÊNCIA (Φ_C)
    # -------------------------------------------------------------------------
    def _compute_phi_c(self, data: Dict, latency: float) -> float:
        """Calcula Φ_C a partir da resposta e latência."""
        # Base: 0.95, penaliza latência alta e respostas curtas
        base = 0.95
        usage = data.get("usage", {})
        total_tokens = usage.get("total_tokens", 100)
        # Latência normalizada: se > 5s, penaliza
        latency_penalty = min(0.05, max(0, (latency - 2.0) * 0.005))
        # Tamanho da resposta: se muito curto, penaliza
        completion_tokens = usage.get("completion_tokens", 0)
        length_penalty = 0.01 if completion_tokens < 10 else 0.0
        phi = base - latency_penalty - length_penalty
        return max(0.0, min(1.0, phi))

    # -------------------------------------------------------------------------
    # UTILITÁRIOS
    # -------------------------------------------------------------------------
    async def health_check(self) -> Dict[str, Any]:
        """Verifica a saúde do servidor vLLM."""
        try:
            response = await self._client.get("/health")
            return {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "status_code": response.status_code,
                "model": self.model,
                "base_url": self.base_url
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def list_models(self) -> List[str]:
        """Lista modelos disponíveis no servidor."""
        try:
            response = await self._client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as e:
            logger.error(f"Erro ao listar modelos: {e}")
            return []

# =============================================================================
# EXEMPLO DE USO
# =============================================================================
async def demo():
    async with VLLMClient(
        base_url="http://localhost:8000/v1",
        model="meta-llama/Llama-4-70B-Instruct"
    ) as client:
        # Inferência síncrona
        result = await client.generate(
            prompt="Explique o conceito de coerência quântica em uma frase.",
            system_prompt="Você é um assistente especialista em física quântica.",
            temperature=0.7,
            max_tokens=200
        )
        print(f"Resposta: {result['text']}")
        print(f"Φ_C: {result['phi_c']:.4f}")
        print(f"Latência: {result['latency_seconds']:.2f}s")
        if "temporal_seal" in result:
            print(f"Selo: {result['temporal_seal']}")

        # Streaming
        print("\n--- Streaming ---")
        async for token in await client.generate(
            prompt="Escreva um poema curto sobre a Catedral.",
            stream=True
        ):
            print(token, end="", flush=True)
        print()

if __name__ == "__main__":
    asyncio.run(demo())
