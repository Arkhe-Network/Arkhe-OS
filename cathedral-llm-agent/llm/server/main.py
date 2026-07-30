#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral LLM Server + Agent Integration
Selo: CATHEDRAL-ARKHE-LLM-SERVER-2026-06-16

Servidor FastAPI que expõe:
- Inferência LLM compatível com OpenAI (/v1/chat/completions)
- Endpoint para executar o CathedralAgent (/agent/run)
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

from llm.inference.engine import get_engine
from agent.core.agent_loop import CathedralAgent

app = FastAPI(title="Cathedral ARKHE LLM + Agent Server")

# Instância global do LLM
llm_engine = get_engine()

# Instância global do agente (pode ser singleton ou por requisição)
agent = CathedralAgent(
    llm_engine=llm_engine,
    use_napi=True,
    enable_guardrails=True,
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "cathedral-llm"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 1024


class AgentRunRequest(BaseModel):
    query: str
    max_iterations: Optional[int] = 6


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    """Endpoint compatível com OpenAI para inferência LLM."""
    try:
        messages = [{"role": m.role, "content": m.content} for m in req.messages]
        response = await llm_engine.chat(
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        return {
            "choices": [
                {
                    "message": {"role": "assistant", "content": response},
                    "finish_reason": "stop"
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/run")
async def run_agent(req: AgentRunRequest):
    """
    Executa o CathedralAgent com uma consulta.
    Retorna a resposta final + passos executados.
    """
    try:
        result = await agent.run(req.query)
        return {
            "query": req.query,
            "final_answer": result.get("final_answer"),
            "steps": result.get("steps", []),
            "success": result.get("success", True)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_engine": "loaded",
        "agent": "ready",
        "napi_available": agent.bridge.use_napi
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
