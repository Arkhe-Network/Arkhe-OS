#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral ARKHE v28.2 — Python Bridge to Rust Agent
Selo: CATHEDRAL-ARKHE-v28.2-PY-BRIDGE-2026-06-16

Permite que o código Python existente (agent_loop.py, cathedral_bridge.py)
utilize o agente Rust de forma transparente, com fallback para implementação
pura Python quando os bindings não estiverem disponíveis.
"""

import asyncio
import importlib
from typing import Dict, Any, Optional

# Tenta importar o módulo Rust compilado com maturin
try:
    import cathedral_agent_py  # type: ignore
    RUST_AGENT_AVAILABLE = True
except ImportError:
    RUST_AGENT_AVAILABLE = False
    from agent.core.agent_loop import CathedralAgent as PythonCathedralAgent


class RustCathedralAgentBridge:
    """Wrapper para o agente Rust via PyO3."""
    def __init__(self, name: str, system_prompt: str, model_id: str, planning_strategy: str = "ReAct"):
        if not RUST_AGENT_AVAILABLE:
            raise RuntimeError("Rust agent not available. Install cathedral_agent_py module.")
        self.inner = cathedral_agent_py.PyCathedralAgent(
            name, system_prompt, model_id, planning_strategy,
            short_term_capacity=50, long_term_enabled=True
        )
        self._loop = None

    async def run(self, goal: str) -> str:
        # PyO3 async methods need to be awaited in the same loop
        return await self.inner.run(goal)

    async def close(self):
        pass  # Rust agent does not need explicit close


class HybridAgent:
    """
    Agente híbrido que usa implementação Rust se disponível,
    caso contrário fallback para Python.
    """
    def __init__(self, name: str = "CathedralAgent", use_rust: bool = True, **kwargs):
        self.use_rust = use_rust and RUST_AGENT_AVAILABLE
        if self.use_rust:
            self._impl = RustCathedralAgentBridge(
                name=name,
                system_prompt=kwargs.get("system_prompt", ""),
                model_id=kwargs.get("model_id", "cathedral-llm"),
                planning_strategy=kwargs.get("planning_strategy", "ReAct")
            )
        else:
            from agent.core.agent_loop import CathedralAgent
            self._impl = PythonCathedralAgent(**kwargs)

    async def run(self, goal: str) -> Dict[str, Any]:
        if self.use_rust:
            answer = await self._impl.run(goal)
            return {"final_answer": answer, "success": True, "steps": []}
        else:
            return await self._impl.run(goal)

    async def close(self):
        await self._impl.close()


# Compatibilidade com cathedral_bridge.py existente
async def get_agent(use_rust: bool = True) -> HybridAgent:
    """Factory function para criar agente compatível com a ponte existente."""
    return HybridAgent(use_rust=use_rust)
