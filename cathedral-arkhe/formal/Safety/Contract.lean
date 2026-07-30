/-
  Cathedral Arkhe v17.0 — O Contrato Assimétrico de Segurança.
  Sem dependências de Topologia. Apenas Lógica e FFI.
-/
import Mathlib.Data.Setoid.Basic

namespace Arkhe.Spec

/-- Evidence é um tipo opaco. O Rust (via FFI) decide o que é evidência.
    Pode ser um hash, uma URL, ou uma prova formal serializada. -/
opaque Evidence : Type

/-- O hash da evidência para rastreamento no ledger. -/
opaque EvidenceHash : Evidence → String

/-- Um ponto verificável no domínio fundamental D. -/
structure VerifiablePoint (D : Type) [Setoid D] where
  point : D
  evidence : Evidence
  hash : String

/-- A RELAÇÃO DE FIDELIDADE CONCRETA.
    O Lean importa essa função como um 'opaque' computável via FFI. -/
@[extern "arkhe_rust_check_faithful"]
opaque checkFaithful {D : Type} [Setoid D]
  (serialize : D → String)
  (a b : VerifiablePoint D)
  : Bool

/-- A ESPECIFICAÇÃO FINAL (O Contrato).
    A função Rust 'checkFaithful' é correta SE E SOMENTE SE
    ela espelha perfeitamente a fidelidade teórica entre as órbitas. -/
structure FaithfulContract (D X : Type) (Sd : Setoid D) (Sx : Setoid X)
  (ι : D → X) (serialize : D → String) : Prop where
  correct : ∀ a b : VerifiablePoint D,
    checkFaithful serialize a b ↔
      (Sx.r (ι a.point) (ι b.point) ↔ Sd.r a.point b.point)

end Arkhe.Spec
