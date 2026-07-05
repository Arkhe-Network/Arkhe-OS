# Auditoria — núcleo safe-core

Base: 7 arquivos `.md` (~719 mil linhas, 8.402 blocos de código, centenas de
versões conflitantes). Escopo auditado: o workspace canônico `safe-core-crypto`
+ `safe-core-policy` declarado como "ÚNICA Fonte de Verdade" no `genesis.md`.

## Bugs reais corrigidos

| # | Arquivo | Bug | Correção |
|---|---------|-----|----------|
| 1 | `crypto/src/verify/kani.rs` | Off-by-one: `&uri[11..]` pula o 1º caractere do hash. `"did:arkhe:"` tem **10** caracteres, não 11 → `assert_eq!(len, 64)` falharia. | `&uri[10..]`. |
| 2 | `crypto/src/verify/kani.rs` | Checagem de chave vazia fraca: `if key_bytes[0] != 0` deixa passar `[0,1,0,...]` como "não-vazia". | `let is_empty = key_bytes.iter().all(|&b| b == 0); if !is_empty {...}`. |
| 3 | `crypto/Cargo.toml` | `kani = "0.55.0"` como dev-dependency quebra o resolver — Kani não é crate do Cargo. | Removido; instala via `cargo install kani-verifier`. |
| 4 | `crypto/src/verify/*` | `kani.rs` órfão (nenhum `mod` o incluía) — nunca entrava na crate, logo `cargo kani` não o via. | `verify/mod.rs` + `#[cfg(kani)] mod verify;` no `lib.rs`. |

## Melhorias aplicadas

- `did.rs`: removido `use blake3::Hash;` (import não usado → warning). `hash.into()`
  mantido — `blake3::Hash` implementa `From<Hash> for [u8; 32]`, então compila
  (a sugestão dos logs de trocar por `*hash.as_bytes()` era desnecessária).
- `did.rs`: adicionado getter `pub_key_hash()` e teste `test_did_uri_shape`.
- `threshold.rs`: doc-comment deixando explícito que `MockSigner` é hash, não
  assinatura real; adicionado teste async determinístico.
- Provas Kani isoladas por `cfg(kani)` — `cargo build`/`cargo test` não as tocam.

## Inconsistências no corpus (fora do escopo do núcleo, ficam registradas)

- **Colapso de contexto**: os logs misturam ≥3 versões de `threshold.rs` e ≥2 de
  `did.rs`. Uma variante fabricava `ThresholdSignature { bytes: Vec<u8><u16> }`
  (sintaxe inválida) e `signer_ids`, e dependia de `lattice-safe-threshold-ml-dsa`
  e `kyberlib` — crates inexistentes. A versão mínima adotada aqui não os usa.
- `rust-toolchain.toml` aparece com `nightly-2026-06-01` (data futura/inexistente
  em vários pontos). Não incluído no núcleo; se precisar de Kani, use `nightly`.
- 231 versões de `Cargo.toml` e 1.538 de `crates/**` no corpus — a arquitetura
  ampla (arkhe-*, safe-core-agi/-agents/-llm, brics-pay, scientific-assistant)
  evoluiu ao longo dos logs e não tem fonte de verdade única. Fora do escopo.

## Estado de verificação

Revisão estática apenas — o ambiente de montagem não tinha toolchain Rust nem
acesso a crates.io. Checagens feitas por leitura: resolução de módulos/re-exports,
features de deps (`serde/derive`, `tokio/macros`, `async-trait`), `From<Hash>`
para `[u8;32]`, `AsRef<[u8]>` em `hex::encode`, macros `serde_json::json!` nos
testes. Nenhum erro de compilação previsto. Confirmação final: `cargo test` local.
