# safe-core — núcleo canônico

Workspace Cargo reconstruído a partir da "ÚNICA Fonte de Verdade" declarada no
`genesis.md`, com as correções aplicadas. Contém apenas as duas crates-base:

```
safe-core/
├── Cargo.toml                      # workspace (resolver = "2")
└── crates/
    ├── safe-core-crypto/           # Camada 0+1 — cripto e identidade
    │   ├── Cargo.toml
    │   └── src/
    │       ├── lib.rs
    │       ├── error.rs            # CryptoError
    │       ├── did.rs              # DidArkhe (derivação Blake3, determinística)
    │       ├── threshold.rs        # ThresholdSigner + MockSigner
    │       └── verify/             # provas Kani (só compilam sob `cargo kani`)
    │           ├── mod.rs
    │           └── kani.rs
    └── safe-core-policy/           # Camada 4 — política / Invariante I13
        ├── Cargo.toml
        └── src/
            ├── lib.rs
            └── consensus_guard.rs  # Policy::evaluate (estrutural, sem CoT)
```

## Rodar (localmente — precisa de Rust estável)

```bash
cd safe-core
cargo build
cargo test
# Esperado: 5 testes passando
#   safe-core-crypto: test_did_determinism, test_did_empty_key_fails,
#                     test_did_uri_shape, test_mock_signer_is_deterministic
#   safe-core-policy: test_allows_valid_tool, test_blocks_unregistered_tool
```

## Verificação formal (opcional)

Kani é instalado à parte, **não** é dependência do Cargo:

```bash
cargo install --locked kani-verifier && cargo kani setup
cd crates/safe-core-crypto
cargo kani --harness prove_did_prefix_is_correct
cargo kani --harness prove_did_determinism_symbolic
```

As provas vivem em `src/verify/kani.rs` e só entram na compilação sob `cfg(kani)`,
então não afetam `cargo build`/`cargo test`.

## Correções aplicadas vs. os logs

Veja `AUDIT.md`.

> Nota: este workspace **não** foi compilado no ambiente onde foi montado (sem
> toolchain Rust e sem acesso a crates.io). Foi validado por revisão estática.
> Rode `cargo test` na sua máquina para confirmação final.
