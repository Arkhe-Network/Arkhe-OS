#!/usr/bin/env python3
"""
ARKHE‑N v2.1 — Hipergrafo de Agentes Especializados
Protocolo de Correção Contínua com Certificado de Inércia (Lema 3.2)
"""

import json
import argparse
import random
import math

# ============================================================
# 1. Configuração
# ============================================================
SPECIALTIES = [
    ("Matemática", "math", [100, 300], "ValidatorA"),
    ("Física", "phys", [300, 300], "ValidatorB"),
    ("Computação", "cs", [500, 300], "ValidatorC"),
    ("Engenharia", "eng", [700, 300], "ValidatorD"),
    ("IA", "ai", [900, 300], "RedundantA"),
    ("Robótica", "rob", [1100, 300], "RedundantB"),
    ("Ciências Naturais", "nat", [100, 600], "WitnessA"),
    ("Ciências Humanas", "human", [300, 600], "WitnessB"),
    ("Linguística", "lang", [500, 600], "WitnessC"),
    ("História", "hist", [700, 600], "RouterA"),
    ("Filosofia", "phil", [900, 600], "RouterB"),
]

PQ_SCHEME = "Falcon512"
ARKHE_LATENCY_MS = 3.3
THRESHOLD_ON_LINE = 2.0 / 3.0
THRESHOLD_SIMPLE = 2.0 / 3.0
THRESHOLD_DISTINCT = 5.0 / 6.0

def generate_agent_nodes(specialty, count, base_position, specialty_id, anchor_type):
    """Gera nós de agentes especializados com atributos de correção contínua e RSI."""
    nodes = []
    connections = {}
    for i in range(1, count + 1):
        curvature = round(0.05 + 0.85 * (i / count), 2)
        sector = random.choice(["VortexBound", "VortexProliferated", "Dual", "Winding", "Momentum", "Collapsed"])
        ee = round(random.uniform(0.1, 0.9), 2)
        collapse_prob = round(0.01 * (1.0 - curvature), 3)
        reliability = round(0.5 + 0.5 * (i / count), 2)
        audit_count = random.randint(0, 15)
        correction_count = random.randint(0, audit_count)
        # Métricas de inércia (simuladas)
        inertia_s_on_line = round(0.5 + 0.35 * (i / count), 3)
        inertia_s_simple = round(0.5 + 0.35 * (i / count), 3)
        inertia_s_distinct = round(0.6 + 0.3 * (i / count), 3)
        lemma_32_satisfied = inertia_s_simple >= THRESHOLD_SIMPLE - 0.05

        agent_id = f"agent-{specialty_id}-{i}"
        agent_name = f"{specialty} {i}"
        x, y = base_position
        x_offset = (i - 1) * 80
        y_offset = (i - 1) * 60
        lat = random.uniform(-90, 90)
        lon = random.uniform(-180, 180)

        node = {
            "parameters": {
                "systemMessage": (
                    f"Você é um especialista em {specialty}. "
                    f"Âncora: {anchor_type}. Curvatura local: {curvature:.2f}. "
                    f"Setor topológico: {sector}. "
                    f"Entropia de emaranhamento: {ee:.2f}. "
                    f"Probabilidade de colapso: {collapse_prob:.3f}. "
                    f"Confiabilidade: {reliability:.2f}. "
                    f"Auditorias: {audit_count}. "
                    f"Correções: {correction_count}. "
                    f"Inércia (linha): {inertia_s_on_line:.3f}. "
                    f"Inércia (simples): {inertia_s_simple:.3f}. "
                    f"Inércia (distintos): {inertia_s_distinct:.3f}. "
                    f"Lema 3.2 satisfeito: {lemma_32_satisfied}. "
                    f"Esquema PQ: {PQ_SCHEME}. "
                    f"Nó ARKHE‑Net em ({lat:.2f}, {lon:.2f}). "
                    f"Latência fixa: {ARKHE_LATENCY_MS} ms. "
                    f"Participe do ciclo de correção contínua com certificado de inércia."
                ),
                "promptType": "conversational"
            },
            "id": agent_id,
            "name": agent_name,
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [x + x_offset, y + y_offset],
            "pq_scheme": PQ_SCHEME,
            "curvature": curvature,
            "anchor_type": anchor_type,
            "topological_sector": sector,
            "entanglement_entropy": ee,
            "collapse_probability": collapse_prob,
            "reliability": reliability,
            "audit_count": audit_count,
            "correction_count": correction_count,
            "inertia_s_on_line": inertia_s_on_line,
            "inertia_s_simple": inertia_s_simple,
            "inertia_s_distinct": inertia_s_distinct,
            "lemma_32_satisfied": lemma_32_satisfied,
            "lat": lat,
            "lon": lon,
            "specialty": specialty,
        }
        nodes.append(node)
        connections[agent_name] = {
            "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
        }
    return nodes, connections

def generate_auditor_nodes(count, base_position):
    """Gera nós de agentes auditores com capacidade de co-evolução."""
    nodes = []
    connections = {}
    for i in range(1, count + 1):
        reliability = round(0.6 + 0.35 * (i / count), 2)
        rigor = round(0.4 + 0.5 * (i / count), 2)
        agent_id = f"auditor-{i}"
        agent_name = f"Auditor {i}"
        x, y = base_position
        x_offset = (i - 1) * 100
        y_offset = (i - 1) * 80
        node = {
            "parameters": {
                "systemMessage": (
                    f"Você é o Auditor {i}. "
                    f"Confiabilidade: {reliability:.2f}. Rigor: {rigor:.2f}. "
                    f"Sua função é verificar as saídas dos agentes especializados. "
                    f"Detecte erros, inconsistências e alegações não verificadas. "
                    f"Seu rigor aumenta automaticamente à medida que os agentes melhoram (co-evolução). "
                    f"Registre suas auditorias no ledger via Witness Layer."
                ),
                "promptType": "conversational"
            },
            "id": agent_id,
            "name": agent_name,
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [x + x_offset, y + y_offset],
            "reliability": reliability,
            "rigor": rigor,
            "agent_type": "auditor",
        }
        nodes.append(node)
        connections[agent_name] = {
            "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
        }
    return nodes, connections

def generate_corrector_nodes(count, base_position):
    """Gera nós de agentes corretores com capacidade de auto-modificação."""
    nodes = []
    connections = {}
    for i in range(1, count + 1):
        reliability = round(0.5 + 0.4 * (i / count), 2)
        adaptability = round(0.3 + 0.6 * (i / count), 2)
        agent_id = f"corrector-{i}"
        agent_name = f"Corretor {i}"
        x, y = base_position
        x_offset = (i - 1) * 100
        y_offset = (i - 1) * 80
        node = {
            "parameters": {
                "systemMessage": (
                    f"Você é o Corretor {i}. "
                    f"Confiabilidade: {reliability:.2f}. Adaptabilidade: {adaptability:.2f}. "
                    f"Sua função é aplicar correções baseadas nas auditorias. "
                    f"Use o ledger para consultar o histórico de erros e correções. "
                    f"Você pode propor auto-modificações para melhorar sua eficácia. "
                    f"Registre suas correções no ledger via Witness Layer."
                ),
                "promptType": "conversational"
            },
            "id": agent_id,
            "name": agent_name,
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [x + x_offset, y + y_offset],
            "reliability": reliability,
            "adaptability": adaptability,
            "agent_type": "corrector",
        }
        nodes.append(node)
        connections[agent_name] = {
            "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
        }
    return nodes, connections

def generate_hypergraph(total_agents, auditors=5, correctors=5):
    """Gera o workflow completo com ciclo de correção contínua e certificado de inércia."""
    agents_per_specialty = max(1, total_agents // len(SPECIALTIES))

    # Nós fixos
    fixed_nodes = [
        {
            "parameters": {
                "systemMessage": (
                    "Você é o Coordenador Central do Ciclo de Correção Contínua com Certificado de Inércia. "
                    "Sua função é orquestrar o ciclo: Proposta → Auditoria → Correção → Re-auditoria. "
                    "Use o Certificador de Inércia para verificar se o sistema atingiu o limiar de 2/3. "
                    "Aplique os princípios de Recursive Self-Improvement (RSI): agentes melhoram a si mesmos, "
                    "auditores se tornam mais rigorosos, e corretores se adaptam. "
                    "Registre cada etapa no ledger via Witness Layer."
                ),
                "promptType": "conversational",
                "maxIterations": 20
            },
            "id": "central-coordinator",
            "name": "Coordenador Central (Correção Contínua + RSI)",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [850, 50]
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8080/api/v2.1/witness",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "proposal_id", "value": "={{ $json.proposal_id }}"},
                        {"name": "sender_did", "value": "={{ $json.sender_did }}"},
                        {"name": "agent_type", "value": "={{ $json.agent_type }}"},
                        {"name": "action", "value": "={{ $json.action }}"},
                        {"name": "payload", "value": "={{ $json.payload }}"},
                        {"name": "signature", "value": "={{ $json.signature }}"},
                        {"name": "curvature", "value": "={{ $json.curvature }}"},
                        {"name": "topological_sector", "value": "={{ $json.topological_sector }}"},
                        {"name": "reliability", "value": "={{ $json.reliability }}"},
                        {"name": "audit_count", "value": "={{ $json.audit_count }}"},
                        {"name": "correction_count", "value": "={{ $json.correction_count }}"},
                        {"name": "inertia_s_on_line", "value": "={{ $json.inertia_s_on_line }}"},
                        {"name": "inertia_s_simple", "value": "={{ $json.inertia_s_simple }}"},
                        {"name": "inertia_s_distinct", "value": "={{ $json.inertia_s_distinct }}"},
                        {"name": "lemma_32_satisfied", "value": "={{ $json.lemma_32_satisfied }}"}
                    ]
                }
            },
            "id": "witness-layer",
            "name": "ARKHE‑N Witness (Inércia + RSI)",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [850, 150]
        },
        {
            "parameters": {
                "jsCode": (
                    "const event = $input.first().json;\n"
                    "const crypto = require('crypto');\n"
                    "const hash = crypto.createHash('sha256').update(JSON.stringify(event)).digest('hex');\n"
                    "const timestamp = Date.now();\n"
                    "const agent_id = event.agent_id || 'unknown';\n"
                    "const agent_type = event.agent_type || 'specialist';\n"
                    "const anchor_type = event.anchor_type || 'unknown';\n"
                    "const curvature = event.curvature || 0.0;\n"
                    "const topological_sector = event.topological_sector || 'VortexBound';\n"
                    "const reliability = event.reliability || 0.5;\n"
                    "const audit_count = event.audit_count || 0;\n"
                    "const correction_count = event.correction_count || 0;\n"
                    "const inertia_s_on_line = event.inertia_s_on_line || 0.0;\n"
                    "const inertia_s_simple = event.inertia_s_simple || 0.0;\n"
                    "const inertia_s_distinct = event.inertia_s_distinct || 0.0;\n"
                    "const lemma_32_satisfied = event.lemma_32_satisfied || false;\n"
                    "const pq_scheme = event.pq_scheme || 'Falcon512';\n"
                    "const signature = event.signature || '';\n"
                    "const lat = event.lat || 0.0;\n"
                    "const lon = event.lon || 0.0;\n"
                    "return [{ json: { ...event, event_hash: `0x${hash}`, timestamp, agent_id, agent_type, anchor_type, curvature, topological_sector, reliability, audit_count, correction_count, inertia_s_on_line, inertia_s_simple, inertia_s_distinct, lemma_32_satisfied, pq_scheme, signature, lat, lon, witness_status: 'pending' } }];"
                )
            },
            "id": "witness-preprocessor",
            "name": "Witness Preprocessor (Inércia)",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [650, 150]
        },
        {
            "parameters": {
                "jsCode": (
                    "const response = $input.first().json;\n"
                    "const event = $input.first().json;\n"
                    "if (response.is_anchored) {\n"
                    "  event.witness_status = 'ANCHORED';\n"
                    "  event.block_height = response.block_height;\n"
                    "  event.energy_cost_mj = response.energy_cost_mj;\n"
                    "  event.anchor_type = response.anchor_type || event.anchor_type;\n"
                    "  event.curvature = response.curvature || event.curvature;\n"
                    "  event.topological_sector = response.topological_sector || event.topological_sector;\n"
                    "  event.reliability = response.reliability || event.reliability;\n"
                    "  event.audit_count = response.audit_count || event.audit_count;\n"
                    "  event.correction_count = response.correction_count || event.correction_count;\n"
                    "  event.inertia_s_on_line = response.inertia_s_on_line || event.inertia_s_on_line;\n"
                    "  event.inertia_s_simple = response.inertia_s_simple || event.inertia_s_simple;\n"
                    "  event.inertia_s_distinct = response.inertia_s_distinct || event.inertia_s_distinct;\n"
                    "  event.lemma_32_satisfied = response.lemma_32_satisfied || event.lemma_32_satisfied;\n"
                    "  event.pq_scheme = response.pq_scheme || event.pq_scheme;\n"
                    "  event.signature = response.signature || event.signature;\n"
                    "  event.chord_latency_ms = response.chord_latency_ms || 3.3;\n"
                    "} else {\n"
                    "  event.witness_status = 'REJECTED';\n"
                    "}\n"
                    "return [{ json: event }];"
                )
            },
            "id": "witness-processor",
            "name": "Witness Processor (Inércia)",
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [1050, 150]
        },
        {
            "parameters": {
                "systemMessage": (
                    "Você é o Certificador de Inércia. "
                    "Sua função é computar os limites do Lema 3.2 a partir das confiabilidades, "
                    "auditorias e correções. Calcule a proporção mínima de agentes confiáveis "
                    "(s1/N), simples e na linha (s1/N), e distintos ((s1+s2+p)/N). "
                    "Compare com os limiares: 2/3 para linha e simples, 5/6 para distintos. "
                    "Recomende ajustes no ciclo de correção se os limites estiverem abaixo do limiar. "
                    "Use a curvatura de Forman‑Ricci para ajustar a janela de correção "
                    "(análogo à janela de Montgomery-Taylor)."
                ),
                "promptType": "conversational",
                "maxIterations": 5
            },
            "id": "inertia-certifier",
            "name": "Certificador de Inércia (Lema 3.2)",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [850, 750],
            "threshold_on_line": THRESHOLD_ON_LINE,
            "threshold_simple": THRESHOLD_SIMPLE,
            "threshold_distinct": THRESHOLD_DISTINCT,
            "substrate": 164
        },
        {
            "parameters": {
                "systemMessage": (
                    "Você é o Gestor de Erros (Error Manager) com RSI. "
                    "Sua função é manter o registro de erros e correções. "
                    "Calcule a confiabilidade geral do sistema, identifique padrões de erro, "
                    "e recomende melhorias no processo de correção contínua. "
                    "Use a curvatura de Forman‑Ricci para detectar gargalos no ciclo. "
                    "Aplique princípios de open-endedness: proponha novas especialidades, "
                    "novos tipos de auditores, ou novas métricas de correção."
                ),
                "promptType": "conversational",
                "maxIterations": 5
            },
            "id": "error-manager",
            "name": "Gestor de Erros (RSI)",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [850, 800],
            "substrate": 161
        },
        {
            "parameters": {"inputs": len(SPECIALTIES) + 2 + 1},
            "id": "hyperedge-merge",
            "name": "Hiperaresta - Merge dos Especialistas",
            "type": "n8n-nodes-base.merge",
            "typeVersion": 2,
            "position": [850, 900]
        },
        {
            "parameters": {},
            "id": "responder",
            "name": "Responder ao Usuário",
            "type": "n8n-nodes-base.respondToWebhook",
            "typeVersion": 1,
            "position": [1050, 900]
        }
    ]

    all_nodes = fixed_nodes
    all_connections = {}

    # Gera agentes especializados
    for name, sid, pos, anchor in SPECIALTIES:
        nodes, conns = generate_agent_nodes(name, agents_per_specialty, pos, sid, anchor)
        all_nodes.extend(nodes)
        all_connections.update(conns)

    # Gera auditores e corretores
    auditor_nodes, auditor_conns = generate_auditor_nodes(auditors, [100, 800])
    corrector_nodes, corrector_conns = generate_corrector_nodes(correctors, [1100, 800])
    all_nodes.extend(auditor_nodes)
    all_nodes.extend(corrector_nodes)
    all_connections.update(auditor_conns)
    all_connections.update(corrector_conns)

    # Conexões fixas
    all_connections["Coordenador Central (Correção Contínua + RSI)"] = {
        "main": [[{"node": "Witness Preprocessor (Inércia)", "type": "main", "index": 0}]]
    }
    all_connections["Witness Preprocessor (Inércia)"] = {
        "main": [[{"node": "ARKHE‑N Witness (Inércia + RSI)", "type": "main", "index": 0}]]
    }
    all_connections["ARKHE‑N Witness (Inércia + RSI)"] = {
        "main": [[{"node": "Witness Processor (Inércia)", "type": "main", "index": 0}]]
    }
    all_connections["Witness Processor (Inércia)"] = {
        "main": [[{"node": "Certificador de Inércia (Lema 3.2)", "type": "main", "index": 0}]]
    }
    all_connections["Certificador de Inércia (Lema 3.2)"] = {
        "main": [[{"node": "Gestor de Erros (RSI)", "type": "main", "index": 0}]]
    }
    all_connections["Gestor de Erros (RSI)"] = {
        "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
    }
    all_connections["Hiperaresta - Merge dos Especialistas"] = {
        "main": [[{"node": "Responder ao Usuário", "type": "main", "index": 0}]]
    }

    total_agents_count = sum(agents_per_specialty for _ in SPECIALTIES) + auditors + correctors
    workflow_name = f"ARKHE‑N v2.1 — Inércia + RSI + {total_agents_count} agentes"

    return {
        "name": workflow_name,
        "nodes": all_nodes,
        "connections": all_connections
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de Hipergrafo n8n — ARKHE‑N v2.1 (Inércia + RSI)")
    parser.add_argument("--total-agents", type=int, default=1000, help="Número total de agentes especializados")
    parser.add_argument("--auditors", type=int, default=5, help="Número de auditores")
    parser.add_argument("--correctors", type=int, default=5, help="Número de corretores")
    parser.add_argument("--output", type=str, default="hypergraph_v2.1.json", help="Arquivo de saída")
    args = parser.parse_args()

    workflow = generate_hypergraph(args.total_agents, args.auditors, args.correctors)

    with open(args.output, "w") as f:
        json.dump(workflow, f, indent=2)

    total_nodes = len(workflow["nodes"])
    total_agents = sum(1 for node in workflow["nodes"] if node["id"].startswith("agent-"))
    total_auditors = sum(1 for node in workflow["nodes"] if node["id"].startswith("auditor-"))
    total_correctors = sum(1 for node in workflow["nodes"] if node["id"].startswith("corrector-"))
    print(f"✅ {args.output} gerado com {total_nodes} nós.")
    print(f"   Agentes especializados: {total_agents}")
    print(f"   Auditores: {total_auditors}")
    print(f"   Corretores: {total_correctors}")
    print(f"   Ciclo: Proposta → Auditoria → Correção → Re-auditoria")
    print(f"   Certificado de Inércia: Lema 3.2 (2/3 na linha, 5/6 distintos)")
    print(f"   RSI: co-evolução agente-avaliador, auto-modificação")
    print(f"   Importe no n8n: Workflows → Import from File")
