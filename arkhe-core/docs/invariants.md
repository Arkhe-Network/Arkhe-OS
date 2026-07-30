# ARKHE v7.0 — Invariantes Cognitivos (IC1–IC10)

## IC1 — Canonical Identity

- **Conceito**: Cada artifact possui uma identidade canônica única.
- **Formalização**: `∀ a,b: canon_id(a)=canon_id(b) => a=b`
- **Verificação**: TLA+ ✅, Coq ✅, Kani ✅, proptest ✅

## IC2 — Provenance Preservation

- **Conceito**: Toda assertion referencia apenas evidências existentes.
- **Formalização**: `∀ a: EvidenceOf(a) ⊆ EvidenceRegistry`
- **Verificação**: TLA+ ✅, Coq ✅, Kani ✅, proptest ✅

## IC3 — Projection Purity

- **Conceito**: Projeção nunca altera o substrato.
- **Formalização**: `Projection(Substrate) = View` e `Substrate` não é modificado.
- **Verificação**: TLA+ ✅, Coq ✅, Kani ✅, proptest ✅

## IC4 — Determinism

- **Conceito**: Mesmo substrato → mesma projeção.
- **Formalização**: `∀ s1,s2: s1=s2 => Projection(s1)=Projection(s2)`
- **Verificação**: TLA+ ✅, Coq ✅, Kani ✅, proptest ✅

## IC5 — Monotonicity

- **Conceito**: Adicionar informação nunca invalida evidências.
- **Formalização**: `S ⊆ S' ⇒ Claims(S) ⊆ Claims(S')`
- **Verificação**: TLA+ ✅, Coq ✅, Kani 🔄, proptest 🔄

## IC6 — Referential Integrity

- **Conceito**: Nenhuma assertion referencia artifact inexistente.
- **Formalização**: `∀ a: References(a) ⊆ Artifacts`
- **Verificação**: TLA+ ✅, Coq ✅, Kani ✅, proptest ✅

## IC7 — Version Linearity

- **Conceito**: Versões formam DAG (acíclico).
- **Formalização**: `Acyclic(VersionGraph)`
- **Verificação**: TLA+ ✅, Coq ✅, Kani 🔄, proptest 🔄

## IC8 — Temporal Consistency

- **Conceito**: Evidência não pode existir antes do artifact.
- **Formalização**: `∀ e: timestamp(e) >= timestamp(artifact(e))`
- **Verificação**: TLA+ ✅, Coq ✅, Kani 🔄, proptest ✅

## IC9 — Trust Monotonicity

- **Conceito**: Adicionar evidências nunca reduz confiança.
- **Formalização**: `S ⊆ S' ⇒ Confidence(S) <= Confidence(S')`
- **Verificação**: TLA+ ✅, Coq 🔄, Kani 🔄, proptest 🔄

## IC10 — Audit Completeness

- **Conceito**: Todo claim pode ser reconstruído.
- **Formalização**: `∀ c: ∃ a: a.claim = c`
- **Verificação**: TLA+ ✅, Coq ✅, Kani 🔄, proptest 🔄