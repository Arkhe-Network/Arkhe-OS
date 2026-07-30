# ARKHE v7.0 — Matriz de Verificação

| Invariante | TLA+ | Coq | Kani | proptest | Runtime | Responsável |
|------------|:----:|:---:|:----:|:--------:|:-------:|-------------|
| IC1        | ✅   | ✅  | ✅   | ✅       | 🔄      | Identity Engine |
| IC2        | ✅   | ✅  | ✅   | ✅       | 🔄      | Evidence Registry |
| IC3        | ✅   | ✅  | ✅   | ✅       | 🔄      | Projection Engine |
| IC4        | ✅   | ✅  | ✅   | ✅       | 🔄      | Projection Engine |
| IC5        | ✅   | ✅  | 🔄   | 🔄       | 🔄      | Claim Engine |
| IC6        | ✅   | ✅  | ✅   | ✅       | 🔄      | Substrate |
| IC7        | ✅   | ✅  | 🔄   | 🔄       | 🔄      | Version Manager |
| IC8        | ✅   | ✅  | 🔄   | ✅       | 🔄      | Event Store |
| IC9        | ✅   | 🔄  | 🔄   | 🔄       | 🔄      | Trust Engine |
| IC10       | ✅   | ✅  | 🔄   | 🔄       | 🔄      | Audit Engine |

**Legenda**:
- ✅ = Completo
- 🔄 = Em progresso / parcial
- ⬜ = Não iniciado

---

## Pipeline de Garantia

| Camada | Ferramenta | Objetivo |
|--------|------------|----------|
| Especificação Matemática | TLA+ | Modelar estados, transições e invariantes |
| Provas Formais | Coq | Demonstrar propriedades fundamentais |
| Verificação de Implementação | Kani | Provar ausência de violações em funções Rust |
| Testes de Propriedade | proptest | Explorar automaticamente grandes espaços de entrada |
| Testes de Integração | cargo test | Validar comportamento entre módulos |
| Observabilidade | Runtime assertions | Detectar violações operacionais |

**Cobertura Esperada por Estado**:

| Estado | Critério |
|--------|----------|
| **Draft** | Apenas definição conceitual |
| **Specified** | Especificado em TLA+ e documentado |
| **Verified** | Propriedades demonstradas em Coq e/ou Kani |
| **Tested** | Coberto por proptest e testes de integração |
| **Runtime Proven** | Monitorado continuamente em execução |