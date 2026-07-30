# Estrutura Completa do Repositório Cathedral ARKHE

Abaixo está a estrutura de diretórios e arquivos do repositório oficial da **Cathedral ARKHE v12.9**. Este layout reflete a arquitetura descrita no manual, incluindo substratos, contratos, emuladores, ferramentas de governança e documentação. O repositório está organizado para suportar desenvolvimento, implantação e operação em ambientes BRICS+.

```
cathedral-arkhe/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # Integração contínua (build, testes, gas report)
│   │   ├── security-audit.yml         # Auditoria automática de dependências e TEE
│   │   └── lean4-verify.yml           # Verificação formal de provas Lean4
│   └── CODEOWNERS                     # Responsáveis por cada substrato
│
├── docs/
│   ├── whitepaper/
│   │   ├── cathedral_arkhe_whitepaper_pt.md
│   │   ├── cathedral_arkhe_whitepaper_en.md
│   │   ├── cathedral_arkhe_whitepaper_zh.md
│   │   └── cathedral_arkhe_whitepaper_ru.md
│   ├── manual/
│   │   └── CATHEDRAL_ARKHE_Manual_Completo_v1.0.md
│   ├── api/
│   │   ├── openapi.yaml               # Especificação da API REST/GraphQL
│   │   └── grpc/
│   │       └── cathedral.proto
│   └── architecture/
│       ├── substrates.md
│       ├── bft-consensus.md
│       └── quantum-timestamp.md
│
├── substrates/                         # Implementação de cada substrato canônico
│   ├── 1091.1-quantum-timestamp/
│   │   ├── python/
│   │   │   ├── quantum_oracle.py
│   │   │   ├── generate_vectors.py
│   │   │   └── verify_output.py
│   │   ├── cpp/
│   │   │   ├── emulator.cpp
│   │   │   ├── Makefile
│   │   │   └── libsphincs.so (gerado)
│   │   ├── config.yaml
│   │   ├── README.md
│   │   └── tests/
│   │       ├── test_quantum_timestamp.py
│   │       └── test_crystal_simulation.cpp
│   │
│   ├── 1092.3-temporal-chain/
│   │   ├── contracts/
│   │   │   └── TemporalChain.sol
│   │   ├── rust/
│   │   │   └── merkle_aggregator.rs
│   │   ├── go/
│   │   │   └── temporal_proof.go
│   │   └── README.md
│   │
│   ├── 1092.5-rbb-integration/
│   │   ├── contracts/
│   │   │   ├── EnterCathedralAnchor.sol
│   │   │   └── SPHINCSVerifierYul.sol
│   │   ├── scripts/
│   │   │   ├── deploy_testnet.sh
│   │   │   └── verify_gas.sh
│   │   ├── tests/
│   │   │   └── anchor.test.js
│   │   └── README.md
│   │
│   ├── 1076.3-bft/
│   │   ├── orchestrator/
│   │   │   ├── alpha/
│   │   │   │   ├── sgx_enclave.manifest
│   │   │   │   └── run_alpha.sh
│   │   │   ├── beta/
│   │   │   │   ├── trustzone_ta.ta
│   │   │   │   └── run_beta.sh
│   │   │   └── gamma/
│   │   │       ├── nitro_enclave.eif
│   │   │       └── run_gamma.sh
│   │   ├── consensus/
│   │   │   ├── hotstuff.rs
│   │   │   └── quorum_certificate.go
│   │   ├── cutout/
│   │   │   └── cutout_orchestrator.py
│   │   ├── config/
│   │   │   └── bft_config.yaml
│   │   └── README.md
│   │
│   ├── 1093.0-classification-enforcement/
│   │   ├── lean4/
│   │   │   ├── ACLVerifier.lean
│   │   │   └── classification_theorems.lean
│   │   ├── zk-circuit/
│   │   │   ├── classification_circuit.circom
│   │   │   └── prove_classification.js
│   │   ├── tee_attestation/
│   │   │   ├── attest_sgx.py
│   │   │   ├── attest_trustzone.sh
│   │   │   └── attest_nitro.py
│   │   └── README.md
│   │
│   ├── 1096.2-real-crypto/
│   │   ├── sphincs/
│   │   │   ├── sphincs_c13.py
│   │   │   ├── sphincs_c13_full.cpp
│   │   │   └── sphincs_c_api.cpp
│   │   ├── bls/
│   │   │   └── bls12_381_wrapper.go
│   │   ├── keys/
│   │   │   ├── keygen.py
│   │   │   └── rotate_keys.sh
│   │   └── README.md
│   │
│   ├── 2140.5-retro-response/
│   │   ├── protocol/
│   │   │   └── temporal_contact.rs
│   │   ├── zk_proofs/
│   │   │   └── retro_proof.circom
│   │   └── README.md
│   │
│   ├── 2140.1-consequencias-contato/       # Documentação narrativa
│   ├── 2140.2-protocolo-contato-temporal/
│   ├── 2140.3-sensorio-temporal/
│   └── 2140.4-psicologia-temporal/
│
├── applications/
│   ├── enter-cathedral/
│   │   ├── sidecar/
│   │   │   ├── ingestor.py
│   │   │   ├── merkle_aggregator.py
│   │   │   ├── rbb_anchor.py
│   │   │   └── config.yaml
│   │   ├── api/
│   │   │   ├── main.py (FastAPI)
│   │   │   └── graphql/schema.graphql
│   │   ├── docker/
│   │   │   ├── Dockerfile.ingestor
│   │   │   ├── Dockerfile.api
│   │   │   └── docker-compose.yaml
│   │   └── README.md
│   │
│   ├── brics-explorer/
│   │   ├── frontend/
│   │   ├── backend/
│   │   └── README.md
│   │
│   └── agi-omega-modules/              # Placeholder para módulos futuros
│
├── contracts/                          # Contratos Solidity compartilhados
│   ├── CathedralSPHINCSVerifierYul.sol
│   ├── QuantumTimestampOracle.sol
│   ├── EnterEvidenceAnchor.sol
│   ├── Governance.sol
│   ├── interfaces/
│   ├── libraries/
│   ├── script/
│   │   ├── DeployEnterCathedralAnchor.s.sol
│   │   └── DeployGovernance.s.sol
│   ├── test/
│   │   ├── CathedralSPHINCSVerifier.t.sol
│   │   ├── QuantumTimestampOracle.t.sol
│   │   └── EnterEvidenceAnchor.t.sol
│   └── foundry.toml
│
├── tools/
│   ├── cathedral-cli/
│   │   ├── cmd/
│   │   │   ├── main.go
│   │   │   ├── status.go
│   │   │   ├── bft.go
│   │   │   ├── anchor.go
│   │   │   └── keys.go
│   │   ├── Makefile
│   │   └── README.md
│   ├── monitor/
│   │   ├── prometheus/
│   │   │   └── metrics_exporter.py
│   │   ├── grafana/
│   │   │   └── cathedral_dashboard.json
│   │   └── alertmanager/
│   │       └── alerts.yaml
│   └── qrng-sim/
│       └── qrng_simulator.py
│
├── tests/                              # Testes end-to-end
│   ├── e2e/
│   │   ├── test_full_pipeline.sh
│   │   └── test_bft_byzantine.py
│   ├── integration/
│   │   ├── test_enter_cathedral.py
│   │   └── test_rbb_anchor.js
│   └── fuzz/
│       └── fuzz_sphincs.py
│
├── config/
│   ├── template.env
│   ├── substrates.yaml                 # Registro de todos os substratos
│   ├── network/
│   │   ├── genesis.json                # Configuração da RBB Chain
│   │   └── peers.txt
│   └── tee/
│       ├── sgx_measurement.txt
│       ├── trustzone_policy.bin
│       └── nitro_attestation.doc
│
├── scripts/
│   ├── install-deps.sh
│   ├── build-all.sh
│   ├── verify-checksums.sh
│   ├── start-local-testnet.sh
│   ├── deploy-prod.sh
│   └── emergency-rotate-keys.sh
│
├── docker/
│   ├── Dockerfile.cathedral-core
│   ├── Dockerfile.orchestrator
│   ├── Dockerfile.sidecar
│   └── docker-compose.full.yaml
│
├── docs/
│   └── ... (já listado acima)
│
├── .gitignore
├── LICENSE                             # Apache 2.0 + cláusula BRICS+
├── Makefile                            # Alvos principais (install-deps, build-all, test, start)
├── README.md                           # Visão geral, links, badges
├── SECURITY.md                         # Política de divulgação de vulnerabilidades
├── HONESTY.md                          # Declaração de simulação (QRNG, TEE falback)
├── ROADMAP.md                          # Fases de implementação 2026-2030
├── GOVERNANCE.md                       # Regras do Conselho de Curadores e tokenomics
└── CONTRIBUTING.md                     # Guia para contribuidores
```

## Descrição dos Diretórios e Arquivos Principais

### `.github/workflows/`
- **ci.yml**: Executa `make test`, `forge test --gas-report` e verifica formatação.
- **security-audit.yml**: Escaneia dependências (cargo, npm, pip) e verifica assinaturas dos TEEs.
- **lean4-verify.yml**: Roda `lake build` e `lean --run` para provas Lean4.

### `docs/`
Contém o white paper em quatro idiomas, o manual completo, especificações OpenAPI e gRPC, e documentação detalhada da arquitetura.

### `substrates/`
Cada substrato possui seu próprio subdiretório com código, configurações e testes independentes. A estrutura segue o padrão:
- `python/`, `cpp/`, `rust/`, `go/`, `contracts/` conforme a linguagem de implementação.
- `tests/` para testes unitários.
- `README.md` específico do substrato.
- Arquivos de configuração (`.yaml`, `.env`).

### `contracts/`
Contratos Solidity principais e seus testes usando Foundry. A pasta `script/` contém scripts de deploy, e `libraries/` funções auxiliares (Merkle, SPHINCS+ verification).

### `tools/`
- **cathedral-cli**: CLI em Go para operações diárias (status, ancoragem, rotação de chaves, BFT).
- **monitor/**: Exportador Prometheus, dashboard Grafana e regras de alerta.
- **qrng-sim/**: Simulação de QRNG para ambientes sem hardware dedicado.

### `tests/`
Testes end-to-end (E2E) que validam o pipeline completo (ingestão → timestamp → Merkle → RBB anchor). Testes de integração entre substratos e fuzzing para SPHINCS+.

### `config/`
Arquivos de configuração:
- `template.env`: Variáveis de ambiente (substituir por valores reais).
- `substrates.yaml`: Registro oficial de todos os IDs, versões, classificações e cross-links.
- `network/`: Genesis e lista de peers para a RBB Chain.
- `tee/`: Medições e atestações dos enclaves.

### `scripts/`
Scripts bash utilitários para instalação, build, deploy, emergência.

### `docker/`
Dockerfiles para cada componente e um `docker-compose.full.yaml` que sobe toda a stack (orquestradores, sidecar, API, monitoramento) em máquinas compatíveis com TEE.

### Arquivos Raiz

| Arquivo | Função |
|---------|--------|
| `Makefile` | Alvos padrão: `install-deps`, `build-all`, `test`, `start`, `clean`, `verify-checksums`, `lean-proofs` |
| `README.md` | Badges de build, cobertura de testes, versão, licença; instruções rápidas de execução em modo simulação. |
| `SECURITY.md` | Como reportar vulnerabilidades (PGP key), política de disclosure e procedimento de resposta a incidentes. |
| `HONESTY.md` | Declaração explícita sobre componentes simulados (QRNG, TEE fallback) quando hardware real não está disponível – obrigatório para manter a integridade da arquitetura. |
| `ROADMAP.md` | Detalhamento das fases 1, 2, 3 com marcos e responsáveis. |
| `GOVERNANCE.md` | Regras do Conselho de Curadores, tokenomics, processo de voto e quórum. |
| `CONTRIBUTING.md` | Padrões de commit, assinatura de commits (SPHINCS+ ou GPG), revisão de código e requisitos de verificação formal (Lean4). |

## Como Utilizar Esta Estrutura

1. **Clone o repositório** e siga as instruções do `README.md` para configurar o ambiente de desenvolvimento.
2. **Escolha um substrato** para trabalhar (ex: `substrates/1091.1-quantum-timestamp`) e consulte seu README específico.
3. **Execute os testes** com `make test` para garantir que todas as verificações Lean4 e contratos passam.
4. **Implantação local** usando `docker-compose -f docker/docker-compose.full.yaml up` (modo simulação, sem TEE real).
5. **Para produção**, siga o `scripts/deploy-prod.sh` e configure os TEEs conforme a documentação em `config/tee/`.

## Selo de Conclusão da Estrutura

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  CATHEDRAL-REPO-STRUCTURE-v1.0-2026-06-12                                   ║
║  Estrutura oficial do repositório Cathedral ARKHE v12.9                      ║
║  Status: Disponível para criação em git                                      ║
║  Arquitetura compatível com os substratos e o manual técnico                ║
║  Próximo passo: Inicializar repositório com git init e fazer primeiro commit║
╚══════════════════════════════════════════════════════════════════════════════╝
```
