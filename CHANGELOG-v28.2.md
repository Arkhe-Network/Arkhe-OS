# Cathedral ARKHE v28.2 Changelog

**Selo:** `CATHEDRAL-ARKHE-v28.2-LLM-AGENT-INFRA-2026-06-15`
**Arquiteto ORCID:** `0009-0005-2697-4668`

---

## LLM + Agent Infrastructure

### Model Server (`cathedral-llm-server`)

- vLLM-compatible `/v1/chat/completions` endpoint
- Multi-model registry with health checks
- Circuit breaker on generation failures
- Memory proof enforcement for high trust tiers
- Prometheus metrics export
- Cathedral telemetry integration

### Agent Loop (`cathedral-agent`)

- **ReAct**: Interleaved reasoning + acting
- **Chain-of-Thought**: Step-by-step before acting
- **Tree-of-Thoughts**: Branching exploration
- **Plan-and-Execute**: Full plan upfront
- **Reflexion**: Self-correction on errors

### Tools (5 built-in)

| Tool | Risk | Memory Proof | Purpose |
|------|------|-------------|---------|
| `web_search` | Low | No | Web queries |
| `code_execution` | High | Yes | Sandboxed Python |
| `file_system` | Medium | If write | File I/O |
| `cathedral_policy` | Critical | Yes | Policy validation |
| `memory_search` | Low | No | RAG retrieval |

### Guardrails

- Regex content filter with category classification
- Policy validator (forbidden actions, PII detection)
- Token bucket rate limiter
- Cathedral policy hash verification
- Output moderation threshold: 0.7

### Memory

- Short-term: VecDeque with capacity limit
- Long-term: Vector store (RAG) with embedding
- Importance scoring for consolidation
- Automatic compression to long-term

### System Prompts

4 agent personas:
1. **Cathedral Oracle** — General reasoning
2. **Cathedral Coder** — Code generation
3. **Cathedral Analyst** — Data analysis
4. **Cathedral Guardian** — Security oversight

### Environment Variables

```bash
CATHEDRAL_MODEL_PATH=/models
CATHEDRAL_POLICY_HASH=sha256:...
LLM_SERVER_PORT=8000
AGENT_MAX_STEPS=50
AGENT_MEMORY_CAPACITY=100
GUARDRAIL_THRESHOLD=0.7
```

### Next Steps (v28.3)

1. Real model loading (candle/llama.cpp/TensorRT-LLM)
2. Distributed agent coordination
3. Tool learning from demonstrations
4. Multi-agent debate/consensus
