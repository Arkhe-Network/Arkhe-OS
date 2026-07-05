# Análise do Repositório — 2026-07-04

Análise factual, baseada apenas no que existe em disco. Sem selos, sem scores inflados.

## 1. Visão geral

O repositório tem cerca de 90 diretórios de nível superior e **986 arquivos soltos na raiz** (278 .py, 178 .md, 81 .rs, 36 PDFs, modelos .gguf, zips, imagens). Há inclusive uma cópia aninhada do próprio repositório (`sasc-v34.8-ω-__-real-implementation-engine/` dentro dele mesmo) e o llama.cpp vendorizado inteiro. Isso não é um projeto de software — é um arquivo de trabalho acumulado. Nenhuma ferramenta (cargo, pytest, CI) consegue operar de forma confiável sobre essa estrutura.

## 2. Git

O histórico tem **11 commits no total**, todos de um único autor, com o último em **2026-05-03** — dois meses atrás. Existem **2.640 mudanças não commitadas** no working tree, e o branch atual é `QC-0892` (não `master`). Na prática, o git não está rastreando o trabalho: quase tudo que foi produzido desde maio vive fora do controle de versão.

## 3. Rust — o que existe de verdade

O workspace Cargo real tem 6 members, e todos os Cargo.toml existem:

O `kernel` (arkhe-kernel) tem **921 linhas de Rust em 6 arquivos** (temporal_chain, model_loader, inference_loop, qip_engine, qart_engine, main). Sem `todo!()` ou `unimplemented!()` — é pequeno, mas parece coeso. Os bindings (cli, python, wasm) e o sagemaker-proxy têm 1 arquivo .rs cada. Em `crates/` existem apenas `safe-core-crypto` e `safe-core-policy`.

**Não foi possível rodar `cargo check`**: o sandbox de análise não tem Rust e a instalação foi bloqueada pela rede. Atenção: o workspace declara `edition = "2024"`, que exige Rust ≥ 1.85. Compilar localmente é o teste que falta.

## 4. Python — o que roda e o que não roda

O pytest coleta **1.508 testes**, mas **25 módulos de teste nem importam** (dependências ausentes, ex.: `polynomial_arkhe`). Numa amostra executada (test_arklib, test_agentfield_bridge, arkhe_os_integral_test): **32 passaram, 27 falharam, 1 erro** — aproximadamente metade quebrada, incluindo testes async mal configurados.

## 5. O que os documentos descrevem mas NÃO existe no repo

Isto é o ponto mais importante. Os documentos colados na conversa (selos "ARKHE-SDK-COMPLETE", "INTEGRACOES-PRIORITARIAS v1.0/v2.0") descrevem código que **não está em disco**:

- O "ARKHE SDK" Rust com 9 crates (arkhe-sdk-kernel, arkhe-sdk-boundary, arkhe-sdk-provenance, arkhe-sdk-mcp...) **não existe**. O diretório `arkhe-sdk/` real é um pacote **Python** com 14 arquivos.
- `crates/arkhe-isolation-kernel` com `i1_no_cross_session_memory.rs` (citado no memo de purge) **não existe**.
- O diretório `specs/tla/` com I9_AcyclicAuthority.tla e I3_CacheOwnership.tla **não existe**. Nenhuma validação TLC foi rodada.
- BoundaryG, ProvenanceEngine, Evidence Bus, MCP servers — existem apenas como texto em documentos, não como código.

Os selos "✅ Concluído" nesses documentos descrevem intenções, não entregas. O próprio memorando de verificação (score 58-72/100) já tinha identificado esse padrão — e depois foi ele mesmo contaminado por um "parecer executivo" de 88/100.

## 6. Estado real, em uma frase

Existe um kernel Rust pequeno (~1k linhas) possivelmente compilável, um conjunto de testes Python meio quebrado, e uma quantidade enorme de documentos gerados por IA descrevendo sistemas que nunca foram escritos.

## 7. Próximos passos recomendados (ordem estrita)

1. **Commitar ou descartar** as 2.640 mudanças pendentes. Decidir o que é código e o que é arquivo morto.
2. **Quarentena**: mover os 986 arquivos soltos da raiz para `archive/` (a pasta já existe). Manter na raiz apenas o workspace Cargo, `tests/`, `src/` e docs essenciais.
3. **Rodar `cargo check --workspace`** na sua máquina (Rust ≥ 1.85). Esse é o único "score" que importa agora: compila ou não compila.
4. **Consertar a coleta do pytest**: criar um `requirements.txt` real, fazer os 25 módulos importarem ou movê-los para quarentena, e chegar a uma suíte onde 100% dos testes coletados executam (mesmo que alguns falhem).
5. Só depois disso: decidir **um** módulo para evoluir (sugestão: `kernel/` com temporal_chain) e escrever testes Rust para ele.
6. Não escrever mais documentos de arquitetura até que os passos 3 e 4 estejam verdes.

## 8. Fatos verificados nesta análise

| Item | Valor |
|---|---|
| Commits no git | 11 (último: 2026-05-03) |
| Mudanças não commitadas | 2.640 |
| Arquivos soltos na raiz | 986 |
| Linhas de Rust no kernel | 921 (6 arquivos, 0 stubs) |
| Members do workspace Cargo | 6 (todos com Cargo.toml presente) |
| Testes Python coletados | 1.508 |
| Módulos de teste que não importam | 25 |
| Amostra executada | 32 pass / 27 fail / 1 erro |
| SDK Rust de 9 crates dos documentos | não existe em disco |
| specs/tla/ (I9, I3) | não existe em disco |
