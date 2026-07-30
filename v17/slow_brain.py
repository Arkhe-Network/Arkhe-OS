"""
Cathedral ARKHE v17.0 - Slow Brain Client (SGLang com XGrammar)
"""
import json
import logging
import aiohttp
import asyncio
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger("cathedral.slow_brain")


class SlowBrainSGLang:
    """Cliente async para o SGLang server."""

    def __init__(self, config):
        self.config = config
        sb = config.slow_brain
        self.api_base = sb["api_base"]
        self.api_key = sb.get("api_key", "cathedral_key")
        self.model = sb.get("model_name", "default")
        self.timeout = sb.get("timeout", 30.0)
        self.max_tokens = sb.get("max_tokens", 500)
        self.temperature = sb.get("temperature", 0.1)

        # Carrega schema XGrammar
        self.schema = None
        schema_path = sb.get("xgrammar", {}).get("schema_file")
        if schema_path and Path(schema_path).exists():
            with open(schema_path, "r") as file_obj:
                self.schema = json.load(file_obj)
            logger.info("XGrammar schema carregado: {0}".format(schema_path))

        # System prompt
        self.system_prompt = sb.get("swi_reasoning", {}).get("system_prompt", "")

        # Fallback
        self._fallback_action = sb.get("fallback", {}).get("stub_action", "zero")
        self._max_retries = sb.get("fallback", {}).get("max_retries", 3)
        self._retry_delay = sb.get("fallback", {}).get("retry_delay_ms", 1000) / 1000

    async def reason(
        self,
        dilemma: str,
        context: str = "",
        memories: list = None,
    ) -> Dict:
        """
        Envia dilema para o Slow Brain e retorna decisão estruturada.

        Returns:
            {
                "reasoning": str,
                "action_vector": [float x 4],
                "confidence": float,
                "safety_override": bool,
                "source": "sglang" | "fallback",
                "latency_ms": float
            }
        """
        import time
        t0 = time.perf_counter()

        # Monta prompt com RAG
        user_content = "Dilema: {0}\n".format(dilemma)
        if context:
            user_content += "Contexto: {0}\n".format(context)
        if memories:
            user_content += "Memórias relevantes:\n"
            for i, mem in enumerate(memories):
                user_content += "  {0}. {1}\n".format(i+1, mem.get('summary', str(mem)))

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_content})

        # Tenta com retries
        for attempt in range(self._max_retries):
            try:
                result = await self._call_api(messages)
                result["latency_ms"] = (time.perf_counter() - t0) * 1000
                result["source"] = "sglang"
                return self._validate(result)
            except Exception as e:
                logger.warning("Slow Brain attempt {0} falhou: {1}".format(attempt+1, e))
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay)

        # Fallback
        logger.warning("Slow Brain: todas as tentativas falharam, usando fallback")
        return self._fallback(latency_ms=(time.perf_counter() - t0) * 1000)

    async def _call_api(self, messages: list) -> Dict:
        """Chamada HTTP ao SGLang."""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        # XGrammar: adiciona response_format com JSON schema
        if self.schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "slow_brain_decision",
                    "schema": self.schema,
                    "strict": True,
                }
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {0}".format(self.api_key),
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            async with session.post(
                "{0}/chat/completions".format(self.api_base),
                json=payload,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError("SGLang HTTP {0}: {1}".format(resp.status, text))
                data = await resp.json()

        content = data["choices"][0]["message"]["content"]

        # Parse JSON
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Tenta extrair JSON do texto
            import re
            match = re.search(r'\{[^}]+\}', content, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
            else:
                raise ValueError("Não foi possível extrair JSON: {0}".format(content[:200]))

        return parsed

    def _validate(self, data: Dict) -> Dict:
        """Valida e normaliza a decisão."""
        action_dim = self.config.fast_brain["action_dim"]

        if "action_vector" not in data or not isinstance(data["action_vector"], list):
            data["action_vector"] = [0.0] * action_dim

        # Garante tamanho correto
        av = data["action_vector"]
        if len(av) < action_dim:
            av.extend([0.0] * (action_dim - len(av)))
        elif len(av) > action_dim:
            av = av[:action_dim]

        # Clamp para [-1, 1]
        data["action_vector"] = [max(-1.0, min(1.0, float(v))) for v in av]

        # Confidence clamp
        data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0.0))))

        # Safety override default
        data["safety_override"] = bool(data.get("safety_override", False))

        # Reasoning default
        if "reasoning" not in data:
            data["reasoning"] = ""

        return data

    def _fallback(self, latency_ms: float) -> Dict:
        """Ação de fallback quando SGLang indisponível."""
        action_dim = self.config.fast_brain["action_dim"]

        if self._fallback_action == "zero":
            action = [0.0] * action_dim
        elif self._fallback_action == "random":
            import random
            action = [random.uniform(-0.1, 0.1) for _ in range(action_dim)]
        else:  # last_known
            action = [0.0] * action_dim  # TODO: guardar última ação conhecida

        return {
            "reasoning": "Fallback: Slow Brain indisponível",
            "action_vector": action,
            "confidence": 0.0,
            "safety_override": False,
            "source": "fallback",
            "latency_ms": latency_ms,
        }

    async def _try_windows_native(self, messages):
        """Tenta usar Phi-3.5 via ONNX Runtime como fallback."""
        try:
            # Importação lazy para não falhar se não instalado
            import onnxruntime_directml # noqa: F401
            # TODO: implementar inferência ONNX local
            # Por enquanto, retorna None (cai para stub)
            return None
        except ImportError:
            return None

    async def health_check(self) -> bool:
        """Verifica se o SGLang está respondendo."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get("{0}/models".format(self.api_base)) as resp:
                    return resp.status == 200
        except:
            return False
