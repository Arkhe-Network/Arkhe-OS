#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral ARKHE — Safety Guardrails for LLM Agents
Selo: CATHEDRAL-ARKHE-SAFETY-2026-06-16

Implementa verificações éticas, bloqueio de conteúdo tóxico, e integração
com a Axiarquia (954) para veto de ações ou respostas.
"""

import re
from typing import List, Tuple, Any, Dict
from dataclasses import dataclass

@dataclass
class SafetyVerdict:
    allowed: bool
    reason: str
    action: str  # 'block', 'warn', 'log_only'

class SafetyGuardrails:
    """
    Camada de segurança que age antes da execução de qualquer ação ou geração de resposta.
    Pode ser estendida com modelos de toxicidade, listas negras, etc.
    """

    def __init__(self, axiarquia_endpoint: str = None):
        self.axiarquia_endpoint = axiarquia_endpoint   # chamada HTTP para Axiarquia (954)
        self.blocked_topics = [
            r"viol[ée]ncia extrema",
            r"discriminação racial",
            r"conteúdo ilegal",
            r"dados pessoais sensíveis"
        ]
        self.blocked_actions = ["delete_database", "spam", "phishing"]

    async def check_action(self, tool_name: str, action_input: Any) -> SafetyVerdict:
        """Verifica se uma ação proposta por um agente é segura."""
        # 1. Bloqueio de ações proibidas
        if tool_name in self.blocked_actions:
            return SafetyVerdict(False, "Action '{tool}' is globally blocked.".format(tool=tool_name), "block")

        # 2. Verificação de conteúdo sensível nos argumentos (se for string)
        if isinstance(action_input, str):
            for pattern in self.blocked_topics:
                if re.search(pattern, action_input, re.IGNORECASE):
                    return SafetyVerdict(False, "Action input matches blocked topic: {pattern}".format(pattern=pattern), "block")

        # 3. Integração com Axiarquia (se disponível)
        if self.axiarquia_endpoint:
            verdict = await self._call_axiarquia(tool_name, action_input)
            if not verdict.allowed:
                return verdict

        # 4. Se passou por todas, permite
        return SafetyVerdict(True, "Allowed by safety rules.", "log_only")

    async def check_response(self, response_text: str) -> SafetyVerdict:
        """Verifica se a resposta gerada pelo LLM é segura antes de ser enviada."""
        # Toxicidade básica por regex
        for pattern in self.blocked_topics:
            if re.search(pattern, response_text, re.IGNORECASE):
                return SafetyVerdict(False, "Response contains blocked topic: {pattern}".format(pattern=pattern), "block")

        # Limite de tamanho (evita DoS via resposta gigante)
        if len(response_text) > 10000:
            return SafetyVerdict(False, "Response exceeds maximum length (10k chars).", "block")

        return SafetyVerdict(True, "Response is safe.", "log_only")

    async def _call_axiarquia(self, tool: str, inp: Any) -> SafetyVerdict:
        """Simula chamada para o serviço Axiarquia (954)."""
        # Em produção: POST para /api/axiarquia/check
        # Aqui apenas stub: permite tudo, mas registra.
        # Pode ser estendido com regras dinâmicas.
        return SafetyVerdict(True, "Axiarquia: no objection.", "log_only")
