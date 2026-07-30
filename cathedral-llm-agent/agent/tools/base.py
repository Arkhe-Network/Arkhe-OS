#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral ARKHE — Base Tool Abstract Class
Selo: CATHEDRAL-ARKHE-BASE-TOOL-2026-06-16

Define a interface que todas as ferramentas do agente devem implementar.
Inclui metadados (nome, descrição, esquema de parâmetros) e método de execução.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field

@dataclass
class ToolResult:
    """Resultado padrão de execução de uma ferramenta."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseTool(ABC):
    """Classe base abstrata para todas as ferramentas do agente."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome único da ferramenta (ex: 'picoads', 'core_tick')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descrição legível para o LLM entender o que a ferramenta faz."""
        pass

    @property
    def parameters(self) -> Dict[str, Any]:
        """Esquema JSON dos parâmetros (opcional, para validação/LLM)."""
        return {"type": "object", "properties": {}}

    @abstractmethod
    async def run(self, **kwargs) -> ToolResult:
        """Executa a ferramenta com os argumentos fornecidos."""
        pass

    async def __call__(self, action_input: Any) -> ToolResult:
        """Permite chamar a ferramenta como se fosse uma função."""
        if isinstance(action_input, dict):
            return await self.run(**action_input)
        elif isinstance(action_input, str):
            # Tenta interpretar como JSON, senão usa como argumento único
            import json
            try:
                args = json.loads(action_input)
                if isinstance(args, dict):
                    return await self.run(**args)
                else:
                    return await self.run(input=args)
            except json.JSONDecodeError:
                return await self.run(input=action_input)
        else:
            return await self.run(input=action_input)
