#!/usr/bin/env python3
"""
ARKHE‑N v2.3 — Hipergrafo com Certificado de Inércia + Otimização de Janela + Derivadas
"""

import json
import argparse
import random

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
THRESHOLD_ON_LINE = 2.0 / 3.0
THRESHOLD_SIMPLE = 2.0 / 3.0
THRESHOLD_DISTINCT = 5.0 / 6.0
THRESHOLD_SIMPLE_DERIV = 0.86864
THRESHOLD_DISTINCT_DERIV = 0.93432
WINDOW_LAMBDA = 1.0 / (2.0 ** 0.5)

def generate_agent_nodes(specialty, count, base_position, specialty_id, anchor_type):
    nodes = []
    connections = {}
    for i in range(1, count + 1):
        reliability = round(0.5 + 0.5 * (i / count), 2)
        deriv_reliability = round(0.1 + 0.8 * (i / count), 3)
        audit_count = random.randint(0, 15)
        correction_count = random.randint(0, audit_count)
        inertia_s_on_line = round(0.5 + 0.35 * (i / count), 3)
        inertia_s_simple = round(0.5 + 0.35 * (i / count), 3)
        inertia_s_distinct = round(0.6 + 0.3 * (i / count), 3)

        # Limites derivados (mais fortes)
        deriv_s_simple = round(0.6 + 0.35 * (i / count), 3)
        deriv_s_distinct = round(0.7 + 0.25 * (i / count), 3)

        lemma_32_satisfied = inertia_s_simple >= THRESHOLD_SIMPLE - 0.05
        lemma_deriv_satisfied = deriv_s_simple >= THRESHOLD_SIMPLE_DERIV - 0.05

        agent_id = f"agent-{specialty_id}-{i}"
        agent_name = f"{specialty} {i}"
        x, y = base_position
        x_offset = (i - 1) * 80
        y_offset = (i - 1) * 60

        node = {
            "parameters": {
                "systemMessage": (
                    f"Você é um especialista em {specialty}. "
                    f"Âncora: {anchor_type}. Confiabilidade: {reliability:.2f}. "
                    f"Derivada da confiabilidade: {deriv_reliability:.3f}. "
                    f"Auditorias: {audit_count}. Correções: {correction_count}. "
                    f"Inércia (linha): {inertia_s_on_line:.3f}. "
                    f"Inércia (simples): {inertia_s_simple:.3f}. "
                    f"Inércia (distintos): {inertia_s_distinct:.3f}. "
                    f"Derivada (simples): {deriv_s_simple:.3f}. "
                    f"Derivada (distintos): {deriv_s_distinct:.3f}. "
                    f"Lema 3.2: {lemma_32_satisfied}. Lema derivado: {lemma_deriv_satisfied}. "
                    f"Esquema PQ: {PQ_SCHEME}. "
                    f"Janela Montgomery-Taylor: λ = {WINDOW_LAMBDA:.4f}. "
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
            "reliability": reliability,
            "deriv_reliability": deriv_reliability,
            "audit_count": audit_count,
            "correction_count": correction_count,
            "inertia_s_on_line": inertia_s_on_line,
            "inertia_s_simple": inertia_s_simple,
            "inertia_s_distinct": inertia_s_distinct,
            "deriv_s_simple": deriv_s_simple,
            "deriv_s_distinct": deriv_s_distinct,
            "lemma_32_satisfied": lemma_32_satisfied,
            "lemma_deriv_satisfied": lemma_deriv_satisfied,
            "window_lambda": WINDOW_LAMBDA,
        }
        nodes.append(node)
        connections[agent_name] = {
            "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
        }
    return nodes, connections

def generate_hypergraph(total_agents, auditors=5, correctors=5):
    agents_per_specialty = max(1, total_agents // len(SPECIALTIES))

    fixed_nodes = [
        {
            "parameters": {
                "systemMessage": (
                    "Você é o Coordenador Central do Ciclo de Correção Contínua com Certificado de Inércia. "
                    "Orquestre o ciclo: Proposta → Auditoria → Correção → Re-auditoria. "
                    "Use o Certificador de Inércia para verificar os limiares de 2/3 e 5/6. "
                    "Aplique a otimização de janela de Montgomery-Taylor. "
                    "Use o Certificador de Derivadas para limites mais fortes (0.86864/0.93432)."
                ),
                "promptType": "conversational",
                "maxIterations": 20
            },
            "id": "central-coordinator",
            "name": "Coordenador Central (Inércia + MT + Derivadas)",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [850, 50]
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://localhost:8080/api/v2.3/witness",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {"name": "proposal_id", "value": "={{ $json.proposal_id }}"},
                        {"name": "sender_did", "value": "={{ $json.sender_did }}"},
                        {"name": "reliability", "value": "={{ $json.reliability }}"},
                        {"name": "deriv_reliability", "value": "={{ $json.deriv_reliability }}"},
                        {"name": "inertia_s_on_line", "value": "={{ $json.inertia_s_on_line }}"},
                        {"name": "inertia_s_simple", "value": "={{ $json.inertia_s_simple }}"},
                        {"name": "inertia_s_distinct", "value": "={{ $json.inertia_s_distinct }}"},
                        {"name": "deriv_s_simple", "value": "={{ $json.deriv_s_simple }}"},
                        {"name": "deriv_s_distinct", "value": "={{ $json.deriv_s_distinct }}"},
                        {"name": "lemma_32_satisfied", "value": "={{ $json.lemma_32_satisfied }}"},
                        {"name": "lemma_deriv_satisfied", "value": "={{ $json.lemma_deriv_satisfied }}"},
                        {"name": "window_lambda", "value": "={{ $json.window_lambda }}"}
                    ]
                }
            },
            "id": "witness-layer",
            "name": "ARKHE‑N Witness (Inércia + MT)",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4,
            "position": [850, 150]
        },
        {
            "parameters": {
                "systemMessage": (
                    "Você é o Certificador de Inércia (Lema 3.2). "
                    "Calcule os limites: s_on_line, s_simple, s_distinct. "
                    "Compare com 2/3 e 5/6. "
                    "Otimize a janela usando Montgomery-Taylor (λ = 1/√2)."
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
            "window_lambda": WINDOW_LAMBDA,
            "substrate": 164
        },
        {
            "parameters": {
                "systemMessage": (
                    "Você é o Certificador de Derivadas (ξ'). "
                    "Aplique o Lema 3.2 à derivada da confiança. "
                    "Calcule s_simple_deriv e s_distinct_deriv. "
                    "Compare com 0.86864 e 0.93432."
                ),
                "promptType": "conversational",
                "maxIterations": 5
            },
            "id": "derivative-certifier",
            "name": "Certificador de Derivadas (ξ')",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [850, 800],
            "threshold_simple_deriv": THRESHOLD_SIMPLE_DERIV,
            "threshold_distinct_deriv": THRESHOLD_DISTINCT_DERIV,
            "substrate": 164
        },
        {
            "parameters": {
                "systemMessage": (
                    "Você é o Otimizador de Janela (Montgomery-Taylor). "
                    "Ajuste a distribuição de confiabilidade para maximizar c(v). "
                    "Use o princípio variacional: v*(s) = cos(√2·λ·s)."
                ),
                "promptType": "conversational",
                "maxIterations": 5
            },
            "id": "window-optimizer",
            "name": "Otimizador de Janela (MT)",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [850, 850],
            "lambda": WINDOW_LAMBDA,
            "substrate": 164
        },
        {
            "parameters": {"inputs": 14},
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

    for name, sid, pos, anchor in SPECIALTIES:
        nodes, conns = generate_agent_nodes(name, agents_per_specialty, pos, sid, anchor)
        all_nodes.extend(nodes)
        all_connections.update(conns)

    # Auditores e corretores (simplificados para o v2.3)
    for i in range(1, auditors + 1):
        node = {
            "parameters": {
                "systemMessage": f"Auditor {i}: Verifique as saídas. Rigor adaptativo.",
                "promptType": "conversational"
            },
            "id": f"auditor-{i}",
            "name": f"Auditor {i}",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [100 + (i-1)*100, 800],
            "agent_type": "auditor"
        }
        all_nodes.append(node)
        all_connections[f"Auditor {i}"] = {
            "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
        }

    for i in range(1, correctors + 1):
        node = {
            "parameters": {
                "systemMessage": f"Corretor {i}: Aplique correções. Auto-modificação.",
                "promptType": "conversational"
            },
            "id": f"corrector-{i}",
            "name": f"Corretor {i}",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 1,
            "position": [1100 + (i-1)*100, 800],
            "agent_type": "corrector"
        }
        all_nodes.append(node)
        all_connections[f"Corretor {i}"] = {
            "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
        }

    all_connections["Coordenador Central (Inércia + MT + Derivadas)"] = {
        "main": [[{"node": "Witness Preprocessor (Inércia)", "type": "main", "index": 0}]]
    }
    all_connections["Certificador de Inércia (Lema 3.2)"] = {
        "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
    }
    all_connections["Certificador de Derivadas (ξ')"] = {
        "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
    }
    all_connections["Otimizador de Janela (MT)"] = {
        "main": [[{"node": "Hiperaresta - Merge dos Especialistas", "type": "main", "index": 0}]]
    }
    all_connections["Hiperaresta - Merge dos Especialistas"] = {
        "main": [[{"node": "Responder ao Usuário", "type": "main", "index": 0}]]
    }

    total_agents_count = sum(agents_per_specialty for _ in SPECIALTIES) + auditors + correctors
    workflow_name = f"ARKHE‑N v2.3 — Inércia + MT + Derivadas + {total_agents_count} agentes"

    return {
        "name": workflow_name,
        "nodes": all_nodes,
        "connections": all_connections
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--total-agents", type=int, default=1000)
    parser.add_argument("--auditors", type=int, default=5)
    parser.add_argument("--correctors", type=int, default=5)
    parser.add_argument("--output", type=str, default="hypergraph_v2.3.json")
    args = parser.parse_args()

    workflow = generate_hypergraph(args.total_agents, args.auditors, args.correctors)

    with open(args.output, "w") as f:
        json.dump(workflow, f, indent=2)

    total_nodes = len(workflow["nodes"])
    print(f"✅ {args.output} gerado com {total_nodes} nós.")
    print(f"   Limiares: 2/3 (linha), 5/6 (distintos), 0.86864/0.93432 (derivadas)")
    print(f"   Janela Montgomery-Taylor: λ = {WINDOW_LAMBDA:.4f}")
    print(f"   Importe no n8n: Workflows → Import from File")
