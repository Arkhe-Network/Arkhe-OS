#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral ARKHE v28.2 — Multi-Agent Orchestrator (Python)
Selo: CATHEDRAL-ARKHE-v28.2-PY-ORCHESTRATOR-2026-06-16

Orquestrador puramente em Python para prototipagem rápida.
Gerencia agentes especializados (Oracle, Coder, Analyst, Guardian)
usando um blackboard compartilhado e workflows configuráveis.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
import uuid
import time

# Importar agentes Python existentes (assumindo que existem)
# Se não existirem, criamos stubs para demonstração
try:
    from agent.core.agent_loop import CathedralAgent as PythonAgent
    from agent.memory.hybrid_memory import HybridMemory
    from agent.guardrails.safety import SafetyGuardrails
    from integration.cathedral_bridge import CathedralBridge
except ImportError:
    # Stubs para demonstração
    class PythonAgent:
        async def run(self, goal: str) -> Dict[str, Any]:
            return {"final_answer": "Stub answer for: {goal}".format(goal=goal), "success": True}
    class HybridMemory: pass
    class SafetyGuardrails: pass
    class CathedralBridge: pass

logger = logging.getLogger("cathedral-orchestrator")

class AgentRole(str, Enum):
    ORACLE = "oracle"
    CODER = "coder"
    ANALYST = "analyst"
    GUARDIAN = "guardian"

@dataclass
class WorkflowStep:
    agent: AgentRole
    action: str          # "query", "generate_code", "analyze", "validate"
    input_key: str       # chave no blackboard para usar como entrada
    output_key: str      # chave onde armazenar o resultado
    condition: Optional[str] = None  # expressão condicional (ex: "guardian_approved")

@dataclass
class Workflow:
    name: str
    steps: List[WorkflowStep]
    max_retries: int = 2

class MultiAgentOrchestrator:
    """
    Orquestrador multi-agente em Python.
    Usa um blackboard (dict compartilhado) para comunicação entre agentes.
    Cada agente é uma instância de `PythonAgent` configurada com seu papel.
    """

    def __init__(self):
        self.agents: Dict[AgentRole, PythonAgent] = {}
        self.blackboard: Dict[str, Any] = {}
        self.workflows: Dict[str, Workflow] = {}
        self.guardian = None  # agente especial para validação final

    def register_agent(self, role: AgentRole, agent: PythonAgent):
        """Registra um agente para um papel específico."""
        self.agents[role] = agent
        if role == AgentRole.GUARDIAN:
            self.guardian = agent

    def register_workflow(self, workflow: Workflow):
        self.workflows[workflow.name] = workflow

    async def run_workflow(self, workflow_name: str, initial_input: Dict[str, Any]) -> Dict[str, Any]:
        """Executa um workflow registrado."""
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            raise ValueError("Workflow '{workflow_name}' not found".format(workflow_name=workflow_name))

        self.blackboard.update(initial_input)
        logger.info("Starting workflow '{workflow_name}' with input keys: {keys}".format(workflow_name=workflow_name, keys=list(initial_input.keys())))

        for step in workflow.steps:
            # Verifica condição se existir
            if step.condition:
                condition_value = self.blackboard.get(step.condition, False)
                if not condition_value:
                    logger.info("Skipping step {action} because condition {condition} is false".format(action=step.action, condition=step.condition))
                    continue

            # Obtém entrada do blackboard
            input_data = self.blackboard.get(step.input_key, {})
            if not input_data:
                logger.warning("No input data for key '{input_key}' in step {action}".format(input_key=step.input_key, action=step.action))
                continue

            # Executa o agente adequado
            agent = self.agents.get(step.agent)
            if not agent:
                raise RuntimeError("No agent registered for role {role}".format(role=step.agent))

            # Constrói o goal para o agente
            goal = self._build_goal(step, input_data)

            # Tentativas com retry
            for attempt in range(workflow.max_retries + 1):
                try:
                    result = await agent.run(goal)
                    if result.get("success", False):
                        output = result.get("final_answer", result)
                        self.blackboard[step.output_key] = output
                        logger.debug("Step {action} completed, output stored at '{output_key}'".format(action=step.action, output_key=step.output_key))
                        break
                    else:
                        error_msg = result.get("error", "Unknown error")
                        logger.warning("Attempt {attempt} failed: {error}".format(attempt=attempt+1, error=error_msg))
                        if attempt == workflow.max_retries:
                            raise RuntimeError("Step {action} failed after retries: {error}".format(action=step.action, error=error_msg))
                except Exception as e:
                    logger.exception("Exception in step {action}".format(action=step.action))
                    if attempt == workflow.max_retries:
                        raise

            # Se guardian existir, valida o resultado após cada passo crítico
            if step.agent == AgentRole.GUARDIAN:
                # Guardian já foi executado – podemos verificar approval
                approval = self.blackboard.get("guardian_approved", False)
                if not approval:
                    logger.error("Guardian vetoed the workflow")
                    return {"status": "blocked", "reason": self.blackboard.get("guardian_reason", "No reason")}

        # Workflow concluído
        final_output = {k: v for k, v in self.blackboard.items() if not k.startswith("_")}
        return {"status": "completed", "result": final_output}

    def _build_goal(self, step: WorkflowStep, input_data: Any) -> str:
        """Constrói o prompt para o agente baseado no tipo de ação."""
        if step.action == "query":
            return "Consultar: {data}".format(data=json.dumps(input_data))
        elif step.action == "generate_code":
            return "Gerar código para: {data}".format(data=input_data)
        elif step.action == "analyze":
            return "Analisar os seguintes dados: {data}".format(data=json.dumps(input_data))
        elif step.action == "validate":
            return "Validar conformidade ética/política: {data}".format(data=json.dumps(input_data))
        else:
            return str(input_data)

    async def direct_query(self, role: AgentRole, query: str) -> str:
        """Consulta direta a um agente sem workflow (útil para testes)."""
        agent = self.agents.get(role)
        if not agent:
            raise ValueError("Agent {role} not registered".format(role=role))
        result = await agent.run(query)
        return result.get("final_answer", "No answer")

# Exemplo de uso
if __name__ == "__main__":
    async def demo():
        # Criar agentes stub (substituir pelos reais)
        oracle = PythonAgent()
        coder = PythonAgent()
        analyst = PythonAgent()
        guardian = PythonAgent()

        orch = MultiAgentOrchestrator()
        orch.register_agent(AgentRole.ORACLE, oracle)
        orch.register_agent(AgentRole.CODER, coder)
        orch.register_agent(AgentRole.ANALYST, analyst)
        orch.register_agent(AgentRole.GUARDIAN, guardian)

        # Definir um workflow simples
        wf = Workflow(
            name="defi_analysis",
            steps=[
                WorkflowStep(AgentRole.ORACLE, "query", "user_question", "oracle_data"),
                WorkflowStep(AgentRole.ANALYST, "analyze", "oracle_data", "analysis"),
                WorkflowStep(AgentRole.GUARDIAN, "validate", "analysis", "guardian_approved"),
                WorkflowStep(AgentRole.CODER, "generate_code", "analysis", "generated_code"),
            ]
        )
        orch.register_workflow(wf)

        result = await orch.run_workflow("defi_analysis", {"user_question": "Qual a tendência de yield na hub DeFi?"})
        print(json.dumps(result, indent=2))

    asyncio.run(demo())
