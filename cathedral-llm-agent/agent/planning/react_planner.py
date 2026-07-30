#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral ARKHE — ReAct Planner for LLM Agents
Selo: CATHEDRAL-ARKHE-REACT-PLANNER-2026-06-16
Integração: TemporalChain, SPHINCS+ (opcional), Axiarquia

Implementa o padrão ReAct (Reasoning + Acting) com registro de cada passo
na TemporalChain, garantindo proveniência e não-repúdio do raciocínio.
"""

import json
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Simulação da TemporalChain (em produção, importar biblioteca real)
class TemporalChainAnchor:
    @staticmethod
    def anchor_step(step_data: Dict[str, Any]) -> str:
        """Ancora um passo na TemporalChain e retorna o hash do bloco."""
        step_json = json.dumps(step_data, sort_keys=True).encode('utf-8')
        block_hash = hashlib.blake3(step_json).hexdigest()
        # TODO: chamar API real da TemporalChain
        print("[TemporalChain] Block anchored: {hash}...".format(hash=block_hash[:16]))
        return block_hash

@dataclass
class ReActStep:
    thought: str        # raciocínio interno
    action: str         # nome da ferramenta a chamar
    action_input: Any   # argumentos para a ferramenta
    observation: Optional[Any] = None
    step_index: int = 0
    timestamp: float = 0.0
    block_hash: str = ""

class ReActPlanner:
    """
    Planejador ReAct que orquestra o ciclo:
    Thought → Action → Observation → (loop) → Final Answer
    Cada passo é ancorado na TemporalChain.
    """

    def __init__(self, llm_engine, max_iterations: int = 5, anchor_to_temporal: bool = True):
        self.llm = llm_engine         # instância de CathedralLLMEngine
        self.max_iterations = max_iterations
        self.anchor = anchor_to_temporal
        self.history: List[ReActStep] = []

    async def plan(self, user_query: str, context: str, tools: Dict[str, Any]) -> List[ReActStep]:
        """
        Executa o loop ReAct até produzir uma resposta final ou esgotar iterações.
        Retorna a lista de passos executados.
        """
        current_prompt = self._build_initial_prompt(user_query, context, tools)
        iteration = 0
        final_answer = None

        while iteration < self.max_iterations and final_answer is None:
            # 1. Thought
            thought, action, action_input = await self._get_thought_and_action(current_prompt)

            # 2. Act: executar ferramenta
            if action == "FINISH":
                final_answer = action_input
                step = ReActStep(
                    thought=thought,
                    action=action,
                    action_input=action_input,
                    observation=None,
                    step_index=iteration,
                    timestamp=time.time()
                )
                self.history.append(step)
                break

            tool_func = tools.get(action)
            if not tool_func:
                observation = "Error: Tool '{action}' not found.".format(action=action)
            else:
                try:
                    observation = await tool_func(action_input)
                except Exception as e:
                    observation = "Tool execution error: {error}".format(error=str(e))

            # 3. Observation
            step = ReActStep(
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
                step_index=iteration,
                timestamp=time.time()
            )

            # 4. Ancoragem temporal (se habilitada)
            if self.anchor:
                step.block_hash = TemporalChainAnchor.anchor_step(asdict(step))

            self.history.append(step)

            # 5. Atualiza prompt para próxima iteração
            current_prompt += "\nThought: {thought}\nAction: {action}\nAction Input: {action_input}\nObservation: {observation}\n".format(thought=thought, action=action, action_input=action_input, observation=observation)

            iteration += 1

        if final_answer is None:
            # Força finalização com mensagem de truncamento
            final_step = ReActStep(
                thought="Maximum iterations reached. Providing partial answer.",
                action="FINISH",
                action_input="I could not complete the reasoning within the allowed steps.",
                step_index=iteration,
                timestamp=time.time()
            )
            self.history.append(final_step)

        return self.history

    async def _get_thought_and_action(self, prompt: str) -> Tuple[str, str, Any]:
        """Chama o LLM para gerar Thought + Action + Action Input no formato ReAct."""
        system = "You are a ReAct agent. Respond in exactly the format:\nThought: ...\nAction: tool_name\nAction Input: ...\n"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
        response = await self.llm.chat(messages, temperature=0.3, max_tokens=512)
        # Parsing simplificado (em produção usar regex ou structured output)
        lines = response.strip().split("\n")
        thought = ""
        action = ""
        action_input = ""
        for line in lines:
            if line.startswith("Thought:"):
                thought = line[len("Thought:"):].strip()
            elif line.startswith("Action:"):
                action = line[len("Action:"):].strip()
            elif line.startswith("Action Input:"):
                action_input = line[len("Action Input:"):].strip()
        return thought, action, action_input

    def _build_initial_prompt(self, query: str, context: str, tools: Dict) -> str:
        tools_desc = "\n".join(["- {name}: {desc}".format(name=name, desc=tool.description) for name, tool in tools.items()])
        return """
Contexto: {context}

Tarefa: {query}

Ferramentas disponíveis:
{tools_desc}

Responda no formato ReAct. Para finalizar, use Action: FINISH com Action Input contendo a resposta final.
""".format(context=context, query=query, tools_desc=tools_desc)
