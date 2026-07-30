#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral ARKHE — Example CLI main entry point
Selo: CATHEDRAL-ARKHE-MAIN-EXAMPLE-2026-06-16

Este script demonstra como instanciar e executar o agente Cathedral
a partir da linha de comando, com opções para LLM local ou remoto,
ancoragem TemporalChain, e integração com o core via bridge.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path (assumindo execução a partir da raiz do projeto)
sys.path.insert(0, str(Path(__file__).parent))

from agent.core.agent_loop import CathedralAgent

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("cathedral-main")

async def run_single_query(agent: CathedralAgent, query: str):
    """Executa uma única consulta e imprime o resultado."""
    print("\n🔍 Query: {query}".format(query=query))
    result = await agent.run(query)
    if result["success"]:
        print("\n✨ Final Answer:")
        print(result["final_answer"])
        print("\n📋 Steps:")
        for step in result["steps"]:
            print("  [{index}] {action}: {observation}...".format(index=step.step_index, action=step.action, observation=str(step.observation)[:100]))
    else:
        print("\n❌ Error: {error}".format(error=result['error']))
    return result

async def interactive_mode(agent: CathedralAgent):
    """Modo interativo (loop contínuo)."""
    print("\n🧠 Cathedral Agent Interactive Mode (type 'exit' or 'quit' to stop)")
    print("─" * 50)
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ("exit", "quit", "q"):
                print("Shutting down...")
                break
            if not user_input:
                continue
            result = await agent.run(user_input)
            print("\n🤖:", result["final_answer"])
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break
        except Exception as e:
            logger.exception("Unexpected error in interactive mode")
            print("\n⚠️ Error: {error}".format(error=e))

async def main():
    parser = argparse.ArgumentParser(
        description="Cathedral ARKHE Agent - LLM-powered autonomous agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with local LLM (vLLM) and napi-rs core
  python main.py --model /path/to/llama --core-mode napi --query "Recommend DeFi yields"

  # Run with HTTP core and stub LLM (no real LLM)
  python main.py --core-url http://localhost:8000 --stub-llm

  # Interactive mode with TemporalChain anchoring
  python main.py --model ./model --anchor --interactive
"""
    )
    parser.add_argument("--query", type=str, help="Single query mode (if not provided, interactive mode)")
    parser.add_argument("--model", type=str, help="Path to local LLM model (vLLM format)")
    parser.add_argument("--stub-llm", action="store_true", help="Use stub LLM (no real model, for testing)")
    parser.add_argument("--memory-db", type=str, default="cathedral_memory.db", help="SQLite path for persistent memory")
    parser.add_argument("--use-vector-db", action="store_true", help="Enable ChromaDB RAG")
    parser.add_argument("--anchor", action="store_true", help="Anchor each step to TemporalChain")
    parser.add_argument("--core-mode", choices=["auto", "http", "napi"], default="auto", help="Core communication mode")
    parser.add_argument("--core-url", type=str, default="http://localhost:8000", help="Core HTTP URL (when mode=http)")
    parser.add_argument("--max-iter", type=int, default=5, help="Max ReAct iterations")
    parser.add_argument("--no-guardrails", action="store_true", help="Disable safety guardrails")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger("cathedral_agent").setLevel(logging.DEBUG)

    # Decide LLM engine: stub or real path
    llm_path = None if args.stub_llm else args.model
    if not args.stub_llm and not args.model:
        print("⚠️ No LLM model provided. Using stub LLM. For real inference, provide --model or use --stub-llm explicitly.")
        llm_path = None  # stub

    # Instantiate agent
    agent = CathedralAgent(
        llm_model_path=llm_path,
        memory_db_path=args.memory_db,
        use_vector_db=args.use_vector_db,
        anchor_to_temporal=args.anchor,
        core_mode=args.core_mode,
        core_http_url=args.core_url,
        max_react_iterations=args.max_iter,
        enable_guardrails=not args.no_guardrails
    )

    try:
        if args.query:
            await run_single_query(agent, args.query)
        else:
            await interactive_mode(agent)
    finally:
        await agent.close()
        print("\n🚪 Agent terminated.")

if __name__ == "__main__":
    asyncio.run(main())
