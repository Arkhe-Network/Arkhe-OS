#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cathedral ARKHE — Hybrid Memory for LLM Agents
Selo: CATHEDRAL-ARKHE-HYBRID-MEMORY-2026-06-16

Integra memória de curto prazo (buffer de conversa) e longo prazo (RAG + SQLite)
com o HybridRecorder do EmbodiedCognitiveCore. Suporta ancoragem opcional na TemporalChain.
"""

import json
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict

# Tentativa de importar o HybridRecorder do core (se disponível)
try:
    from recorder.hybrid_recorder import HybridRecorder
except ImportError:
    # Fallback: implementação stub
    class HybridRecorder:
        def __init__(self, db_path: str = "cathedral_memory.db"):
            self.db_path = db_path
            self._init_db()
        def _init_db(self):
            conn = sqlite3.connect(self.db_path)
            conn.execute("CREATE TABLE IF NOT EXISTS rounds (id INTEGER PRIMARY KEY, timestamp REAL, data TEXT)")
            conn.commit()
            conn.close()
        def record_round(self, round_data: Dict):
            conn = sqlite3.connect(self.db_path)
            conn.execute("INSERT INTO rounds (timestamp, data) VALUES (?, ?)", (time.time(), json.dumps(round_data)))
            conn.commit()
            conn.close()
        def recent_hub_stats(self, n: int = 10) -> List[Dict]:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute("SELECT data FROM rounds ORDER BY timestamp DESC LIMIT ?", (n,))
            rows = cur.fetchall()
            conn.close()
            return [json.loads(row[0]) for row in rows]

class HybridMemory:
    """
    Memória híbrida com:
    - Buffer de curto prazo (conversa atual)
    - Armazenamento persistente via HybridRecorder (SQLite)
    - RAG opcional usando ChromaDB (se disponível)
    - Ancoragem na TemporalChain (opcional)
    """

    def __init__(self, db_path: str = "cathedral_memory.db", use_vector_db: bool = True, anchor_to_temporal: bool = False):
        self.short_term = deque(maxlen=20)  # últimos 20 eventos
        self.recorder = HybridRecorder(db_path)
        self.use_vector_db = use_vector_db
        self.anchor = anchor_to_temporal
        self.vector_store = None

        if use_vector_db:
            try:
                import chromadb
                from chromadb.utils import embedding_functions
                self.chroma_client = chromadb.PersistentClient(path="./chroma_data")
                self.collection = self.chroma_client.get_or_create_collection(
                    name="agent_memory",
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
                )
            except ImportError:
                print("[HybridMemory] ChromaDB not installed. RAG disabled.")
                self.use_vector_db = False

    async def add(self, step: Any, result: Any) -> None:
        """
        Adiciona um passo da execução (thought, action, observation) à memória.
        step: objeto ReActStep ou dict com thought/action/action_input/observation
        result: resultado da ferramenta (ToolResult ou dict)
        """
        if hasattr(step, '__dict__'):
            entry = {
                "type": "step",
                "timestamp": time.time(),
                "step_index": getattr(step, 'step_index', 0),
                "thought": getattr(step, 'thought', ''),
                "action": getattr(step, 'action', ''),
                "action_input": getattr(step, 'action_input', ''),
                "observation": getattr(step, 'observation', None),
                "result": result if isinstance(result, dict) else {"data": str(result)},
                "block_hash": getattr(step, 'block_hash', '')
            }
        else:
            entry = {"type": "step", "timestamp": time.time(), "data": step, "result": result}

        # Memória de curto prazo
        self.short_term.append(entry)

        # Persistência via HybridRecorder
        self.recorder.record_round(entry)

        # RAG: adicionar ao ChromaDB (se disponível)
        if self.use_vector_db and self.collection:
            text = "Thought: {thought} Action: {action} Observation: {observation}".format(
                thought=entry.get('thought',''),
                action=entry.get('action',''),
                observation=entry.get('observation','')
            )
            doc_id = hashlib.blake3(text.encode()).hexdigest()
            self.collection.upsert(
                documents=[text],
                metadatas=[{"timestamp": entry["timestamp"], "type": "step"}],
                ids=[doc_id]
            )

        # Opcional: ancorar na TemporalChain
        if self.anchor:
            await self._anchor_to_temporal(entry)

    async def retrieve(self, query: str, top_k: int = 5) -> str:
        """
        Recupera contexto relevante para a consulta atual.
        Combina: últimos passos do curto prazo + RAG (se disponível).
        Retorna string formatada para o planner.
        """
        context_parts = []

        # 1. Contexto imediato (curto prazo)
        if self.short_term:
            recent = list(self.short_term)[-5:]
            context_parts.append("=== Recent actions ===")
            for item in recent:
                if 'action' in item:
                    context_parts.append("- {action}: {observation}".format(action=item['action'], observation=item.get('observation', '')[:200]))
                else:
                    context_parts.append("- {item}".format(item=item))

        # 2. RAG baseado em similaridade semântica
        if self.use_vector_db and self.collection:
            try:
                results = self.collection.query(query_texts=[query], n_results=top_k)
                if results['documents'] and results['documents'][0]:
                    context_parts.append("=== Relevant past memories ===")
                    for doc in results['documents'][0]:
                        context_parts.append("  • {doc}...".format(doc=doc[:300]))
            except Exception as e:
                print("[HybridMemory] RAG query failed: {error}".format(error=e))

        # 3. Estatísticas recentes do hub (via HybridRecorder, se disponível)
        try:
            hub_stats = self.recorder.recent_hub_stats(5)
            if hub_stats:
                context_parts.append("=== Recent hub statistics ===")
                for stat in hub_stats:
                    context_parts.append("  {stat}".format(stat=stat))
        except Exception:
            pass

        return "\n".join(context_parts) if context_parts else "No relevant context found."

    async def clear_short_term(self) -> None:
        """Limpa a memória de curto prazo (útil para novas sessões)."""
        self.short_term.clear()

    async def get_full_history(self, limit: int = 50) -> List[Dict]:
        """Recupera histórico persistente do banco de dados."""
        conn = sqlite3.connect(self.recorder.db_path)
        cur = conn.execute("SELECT data FROM rounds ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [json.loads(row[0]) for row in rows]

    async def _anchor_to_temporal(self, entry: Dict) -> None:
        """Ancora uma entrada na TemporalChain (stub, em produção integrar com Substrato 1094)."""
        # Em produção: chamada para API da TemporalChain
        import hashlib
        data_json = json.dumps(entry, sort_keys=True)
        block_hash = hashlib.blake3(data_json.encode()).hexdigest()
        print("[HybridMemory] Anchored to TemporalChain: {hash}...".format(hash=block_hash[:16]))
        # Opcional: armazenar hash no próprio registro
        entry["temporal_hash"] = block_hash
