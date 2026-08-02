; invariantes.smt2
; I1: Aciclicidade em DEPENDS_ON
(declare-fun depends_on (Int Int) Bool)
(assert (forall ((v0 Int) (v1 Int) (v2 Int))
  (=> (and (depends_on v0 v1) (depends_on v1 v2))
      (not (depends_on v2 v0)))))

; I2: Cobertura de testes
(declare-fun module_status (Int) Int)  ; 4 = MERGED
(declare-fun has_test_edge (Int) Bool)
(assert (forall ((m Int))
  (=> (= (module_status m) 4) (has_test_edge m))))

; I3: Score válido
(declare-fun module_score (Int) Real)
(assert (forall ((m Int))
  (and (>= (module_score m) 0.0) (<= (module_score m) 100.0))))