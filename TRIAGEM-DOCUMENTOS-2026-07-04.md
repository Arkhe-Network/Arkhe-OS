# Triagem dos 8 documentos enviados — 2026-07-04

Análise por amostragem estruturada (~25 MB, ~700 mil linhas no total). Veredito por arquivo, do mais valioso ao menos.

## Vereditos

### 1. patch.md (67k linhas) — O MAIS VALIOSO
É o único documento com autocrítica funcional: abre diagnosticando o "colapso de contexto" do pipeline multi-agente (versões dessincronizadas, análise de código fantasma como o `threshold-ml-dsa` fabricado, citado 21 vezes justamente para eliminá-lo). Contém 5 iterações do `ThresholdSignature` real do repo e culmina num "código final auto-suficiente" com 29 defeitos alegadamente resolvidos e design trait-based (SafetyVerifier, AgentMemory, mistralrs backend). Referencia os crates REAIS do repo (safe-core-crypto ×64, safe-core-policy ×49).
**Ação: é o candidato a fonte de extração. Mas o selo "29/29 resolvidos" é auto-atribuído — só vale depois de `cargo check` no código extraído.**

### 2. safe-core.md (66k linhas) — PLANO + CÓDIGO EXPANDIDO
Plano de crescimento em pilares (produto, comunidade, visibilidade) mais versões expandidas dos crates safe-core (564 blocos Rust, 13 blocos Lean). Referencia os crates reais (×68/×43). A parte de plano é razoável como norte; o código precisa da mesma validação do patch.md.
**Ação: extrair seções de código que estendam os crates reais de 182 linhas; ignorar cronogramas Q3/Q4.**

### 3. harness.md (25k linhas) — SNIPPETS UTILITÁRIOS
"100+ snippets" + servidor MCP com API rmcp 0.1.4, OAuth 2.1, isolamento Docker/K8s, benchmark SHB. Zero selos, mais pé no chão que os demais. Não referencia os crates safe-core (é genérico).
**Ação: útil como catálogo de referência quando (e se) for implementar servidor MCP. Não é código do projeto.**

### 4. AGI-Descentralizada-Corrigida-v2.md (273 linhas) — JÁ CONHECIDO
A versão corrigida honesta do paper AGI (a que removeu os NIPs fabricados e alongou o roteiro para 30 meses). Documento de visão, não de código.
**Ação: arquivar como norte estratégico (P5+, ano 2+, conforme o próprio memo de purge).**

### 5. agi.md (186k linhas, 6,3 MB) — DOCUMENTAÇÃO MEGALITICA
"AGI 14-Bis — Documentação Completa do Safe-Core v3.0.0, Status: Produção". 1.113 blocos Rust, 239 scores. O status "Produção" é falso — o safe-core real no repo tem 182 linhas com MockSigner. É documentação de um sistema que não existe nessa escala.
**Ação: arquivar. Consultar pontualmente se alguma seção específica for necessária.**

### 6. genesis.md (289k linhas, 10,5 MB) — DUMP ACUMULADO
Concatenação de meses de sessões: Account Abstraction, Taproot Assets/Lightning, instaladores WiX, CDN, causal engines... 1.862 blocos Rust, 304 selos, 533 scores. Inclui até uma cópia do diagnóstico do patch.md. É o histórico bruto do pipeline, não um documento.
**Ação: arquivar como registro histórico. Não usar como fonte de código (versões conflitantes misturadas).**

### 7. safe.md (32k linhas) — SCRIPT GERADOR + CONFIGS
Começa com script Python que gera estrutura de diretórios de config. Zero selos. Conteúdo utilitário mas sobreposto ao safe-core.md.
**Ação: arquivar; usar safe-core.md como fonte primária dessa linha.**

### 8. ao.md (54k linhas) — FILOSOFIA
Arkhé, ontologia e hermenêutica aplicadas a programação, com implementação Rust conceitual. Bem escrito como ensaio; nenhuma conexão com o código real do repo.
**Ação: arquivar como material de escrita/livro (combina com livro-arkhe/), não como spec técnica.**

## Síntese

| Arquivo | Código aproveitável | Ruído | Veredito |
|---|---|---|---|
| patch.md | Alto (se compilar) | Médio | Extrair e validar |
| safe-core.md | Médio | Médio | Extrair seções |
| harness.md | Médio (referência) | Baixo | Guardar como catálogo |
| AGI-Desc-v2.md | — | Baixo | Norte estratégico |
| agi.md | Baixo | Alto | Arquivar |
| genesis.md | Baixo | Muito alto | Arquivar (histórico) |
| safe.md | Baixo | Médio | Arquivar |
| ao.md | — (ensaio) | — | Material de livro |

## Padrão transversal (importante)

Os documentos repetem o ciclo já visto no repo: código gerado → análise crítica honesta → "parecer executivo" que infla o resultado → selo de conclusão sem compilação. O patch.md é o único que NOMEIA esse ciclo — e mesmo ele termina com um selo auto-atribuído. A regra que vale para tudo: **nenhum selo conta; só `cargo check` e `pytest` contam.**

## Próximo passo recomendado

Extrair do patch.md o "monorepo Safe-Core v1.2" final (a última iteração, ignorando as 4 anteriores), montá-lo em disco e rodar `cargo check`. Se compilar, ele substitui/estende os 182 linhas reais dos crates safe-core. Se não compilar, o documento vira archive como os demais.
