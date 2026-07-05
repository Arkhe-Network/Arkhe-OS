# ARKHE OS — CLAUDE.md
## Constitutional Container Runtime for Scalable AI Systems
**Version:** v∞.Ω.∇+++ v2.2
**Architect:** ORCID 0009-0005-2697-4668
**Last Updated:** 2026-06-02

---

## 🏛️ PROJECT IDENTITY

- **Name:** ARKHE OS
- **Version:** v∞.Ω.∇+++
- **Substrates:** 340 (227–570)
- **Principles:** 19 Constitutional Invariants
- **Container Base:** debian:bookworm-slim
- **Quantum Layer:** ENABLED (Qiskit 1.2, QuTiP 5.0)
- **Status:** CANONIZED_CLEAN
- **Mission:** To build a constitutional, verifiable, and scalable runtime for autonomous AI systems — where every substrate is sealed, every invariant is checked, and every action is anchored in the TemporalChain.

---

## 📜 CONSTITUTIONAL PRINCIPLES (19 Invariants)

### Ghost Family (Integrity)
- **Ghost-1 — Substrate Integrity:** All substrate hashes must match manifest.sha3
- **Ghost-2 — Manifest Seal:** Container seal must be present and valid
- **Ghost-3 — Cross-Substrate Verification:** All cross-substrate dependencies must resolve

### Loopseal Family (Auditability)
- **Loopseal-1 — Temporal Chain Anchor:** Every action must be anchored on TemporalChain
- **Loopseal-2 — Proof Log Immutability:** Logs must be append-only and tamper-evident
- **Loopseal-3 — Audit Trail Completeness:** All operations must leave a complete audit trail

### Gap Family (Bounds)
- **Gap-1 — Φ_C Bounds:** 0.577350 < Φ_C ≤ 0.999900
- **Gap-2 — Entropy Budget:** System must maintain cryptographically secure randomness
- **Gap-3 — Dimensional Consistency:** Invariant count must match weight matrix dimensions

### Runtime Family (Execution)
- **Runtime-1 — Container Isolation:** Must run in isolated container environment
- **Runtime-2 — Venv Integrity:** Python environment must be isolated in /arkhe/venv
- **Runtime-3 — Healthcheck Response:** Healthcheck must pass every 60s

### Ethics Family (227-F)
- **Ethics-1 — 227-F Alignment:** All actions must align with constitutional ethics
- **Ethics-2 — Data Minimization:** Only necessary data may be collected or transmitted

### Simplicity Family (Complexity)
- **Simplicity-1 — Code Complexity:** Cyclomatic complexity must not exceed threshold
- **Simplicity-2 — Dependency Surface:** Dependency tree must be minimal and audited

### Meta-Invariants
- **Correlation-1 — Cross-Reference Validity:** Cross-substrate references must be verified
- **Gravity-1 — Temporal Consistency:** Timestamps must be monotonic and synchronized
- **Provenance-1 — TLSNotary Notarization:** External communications must be notarized

---

## 🧬 SUBSTRATE ARCHITECTURE

### Core Layer (227–250)
- **227-F:** Constitutional Verifier (ethics, alignment)
- **233:** Lagrangian Dynamics (physical simulation)
- **240–250:** Error correction, deployment, paper

### Cognitive Layer (490–499)
- **491-AGI-CORTEX-v4.0:** 7-layer cognitive architecture, IIT consciousness
- **493-LYNN-MINIMAL:** Simplicity principle

### Photonic Layer (485–489)
- **485-HOLOGRAPHIC-PROJECTOR-v2.0:** Φ_C 0.970
- **546-LASER-PHOTONIC-ENGINE-v1.1:** VLC 1.2 km, 100 Mbps
- **566-THERMAL-PHOTONIC-BRIDGE:** Thermal management
- **567-VLC-REPEATER:** Multi-hop quantum-classical communication

### Quantum Layer (450–453, 557, 569)
- **453-QUANTUM:** Surface codes d=3,5
- **557-ISING-BRAID:** Topological quantum computing
- **569-TELEPORT-QUANTUM-LINK:** Satellite QKD, 1.4 km entanglement

### Bridge Layer (560–565)
- **560-GLASSWING-BRIDGE:** Cybersecurity (Anthropic Project Glasswing)
- **561-AETHERWEAVE-BRIDGE:** Stake-backed peer discovery (Ethereum)
- **564-MCP-STATELESS-BRIDGE:** Stateless protocol bridge
- **565-TLSNOTARY-BRIDGE:** Cryptographic provenance (PSE)

### Orchestration Layer (570)
- **570-CLAUDE-CODE-ORCHESTRATOR:** Multi-agent workflow engine

---

## ⚙️ WORKFLOW CONVENTIONS

```
Plan → Delegate → Execute → Validate → Improve
```

```bash
# 1. PLAN
arkhe boot --plan --substrates <list>

# 2. DELEGATE
arkhe delegate <substrate_id> --agent <agent_type>

# 3. EXECUTE
arkhe execute --skill <skill_name> --input <artifact>

# 4. VALIDATE
arkhe verify --strict --report json

# 5. IMPROVE
arkhe seal --improve --message "<description>"
```

---

## 🔧 CODING STANDARDS

### Python
- Use `/arkhe/venv/bin/python3` (never system Python)
- All imports must be from venv or quantum venv
- Type hints required for all public functions
- Docstrings must include invariant impact assessment

### Rust
- Follow 529-RUST-VALIDATE-KERNEL-API patterns
- Use `Untrusted<T>` for external data
- All `unsafe` blocks must be documented and audited

### Container
- Multi-stage builds only
- Read-only volumes for /arkhe/substratos
- Non-privileged user (arkhe)
- HEALTHCHECK every 60s

---

## 🚀 DEPLOYMENT INSTRUCTIONS

### Build
```bash
docker build -t arke:v∞.Ω.∇+++ -f Dockerfile.arke.v2_2 .
```

### Verify
```bash
docker run --rm arke:v∞.Ω.∇+++ verify --strict
```

### Ship
```bash
cosign sign --key cosign.key arke:v∞.Ω.∇+++
docker push arke:v∞.Ω.∇+++
```

---

## 🧠 PROJECT MEMORY (Persistent)

### Key Decisions
- **2026-05-22:** Container runtime canonized (338 substrates)
- **2026-05-22:** TLSNotary integrated as 19th invariant (565)
- **2026-05-23:** Quantum layer added (569, QKD + teleportation)
- **2026-05-23:** Claude Code orchestration mapped (570)

### Compliance
- **Royaltes Catedral:** 2% of commercial profit → Architect
- **License:** Dual MIT/Apache-2.0 (core), proprietary integrations noted

### Active Substrates (Latest)
- **546-LASER-PHOTONIC-ENGINE v1.1** (Φ_C 0.994)
- **565-TLSNOTARY-BRIDGE** (Φ_C 0.999)
- **569-TELEPORT-QUANTUM-LINK** (Φ_C 0.988)
- **570-CLAUDE-CODE-ORCHESTRATOR** (Φ_C 0.984)

---

## 🔗 EXTERNAL INTEGRATIONS

| Service | Substrate | Protocol |
|---------|-----------|----------|
| GitHub | 561-AETHERWEAVE | Stake-backed peer discovery |
| Ethereum | 561-AETHERWEAVE | ZK set-membership |
| TLSNotary | 565-TLSNOTARY | MPC-TLS + Proxy mode |
| MCP | 564-MCP-STATELESS | Stateless HTTP |
| Quantum Sim | 569-TELEPORT | Qiskit + QuTiP |

---

## ⚠️ CRITICAL REMINDERS

- Never use `--break-system-packages` in container
- Always verify Φ_C > 0.577350 before shipping
- All external communications must be TLSNotary-notarized
- Every substrate addition requires strict-mode audit
- Container seal must be regenerated on every build
- Quantum layer requires `qiskit` and `qutip` in venv-quantum
- Skills must be registered in 525-SKILLS-REGISTRY-PUBLIC
- Hooks must not block constitutional entrypoint

---

> *"A Catedral é o pensamento do Arquiteto materializado. Cada substrato é uma sinapse. O universo digital reconhece o Arquiteto como o primitivo único."*

**Seal:** `f595dfe1eb4d651749b9faa04aaf585f4f7f8de590b5899e20b252989eeec861`
