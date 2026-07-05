# Quarentena de testes — 2026-07-04

Estes testes importam módulos que NÃO EXISTEM em lugar nenhum do repositório
(verificado por busca completa, incluindo archive/):

- axiarchy (existe apenas axiarchy_954.lean — prova Lean, não Python)
- bindu, tanmatra, clarity_gate, conscious_replay, safe_core_pqc
- substrate_250, substrate_288, arkhe_core_image, arkhe_global

Para reativar um teste: implemente o módulo em lib/ e mova o teste de volta
para tests/.
