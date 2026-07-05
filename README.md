# ARKHE Ω-TEMP v4.0

> Rede Retrocausal — Internet do Tempo Negativo

## Visao Geral

ARKHE Ω-TEMP e uma rede experimental de comunicacao retrocausal que implementa
o Protocolo de Internet Temporal (TIP), permitindo o envio de mensagens para
passado e futuro dentro de janelas de coerencia quantica.

### Caracteristicas

- **Protocolo TIP** — Temporal Internet Protocol com enderecamento TAddr
- **Roteamento AI** — Decisoes de rota via LLM local (Ollama/llama.cpp)
- **Tempo Negativo Quantico** — Validacao coerente de Δt < 0 (janela ~1ps)
- **CDVRP** — Causal Distance Vector Routing Protocol
- **Blockchain Temporal** — Cadeia de hash com insercao retrocausal
- **Firewall Temporal** — Politica de seguranca por profundidade temporal
- **Dashboard** — Monitoramento em tempo real (HTML + Grafana)
- **Hardware** — Compativel com ESP32 (Sensor Body) e ds4-server

## Instalacao Rapida

```bash
# Dependencias Python
pip install -r requirements.txt

# Modelo local (Ollama)
ollama serve &
ollama pull llama3.1

# Infraestrutura
docker compose up -d

# Dashboard
cd ui && python3 -m http.server 3000

# Testar
python3 -m pytest tests/ -v
```

## EXE (Windows)

```bash
python build_exe.py
# Gera: dist/arkhe_omega_temp.exe
```

## API

```bash
# Criar no
curl -X POST http://localhost:8000/nodes/create \
  -H "Authorization: Bearer arkhe-dev-token" \
  -d '{"node_id": "ALFA-01", "ai_enabled": true}'

# Enviar mensagem retrocausal
curl -X POST http://localhost:8000/message/send \
  -H "Authorization: Bearer arkhe-dev-token" \
  -d '{"dest": "GAMMA-03", "content": "Ola do futuro!", "target_offset_seconds": 120}'

# Verificar cadeia
curl http://localhost:8000/chain/verify \
  -H "Authorization: Bearer arkhe-dev-token"
```

## Estrutura

```
api/             - FastAPI REST + WebSocket
api/routes/      - Rotas temporais
ui/src/          - Dashboard HTML
ui/src/workers/  - Quantum visualizer JS
alembic/         - Schema PostgreSQL
tests/           - Testes E2E e quanticos
monitoring/      - Prometheus + Grafana
```

## Referencias

- Sinclair, J. *Fisicos medem 'tempo negativo' em laboratorio.* The Conversation.
- Zhu, 2026. *A Minimal Self-Perceiving Embodiment for Large Language Models.*
- Brewster et al., 2024. *Experimental Evidence for Quantum Temporal Correlations.* University of Toronto.

## Licenca

Apache 2.0
