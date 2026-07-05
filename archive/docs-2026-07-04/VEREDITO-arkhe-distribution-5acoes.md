# Veredito — "ARKHE 5 Ações Descentralização" (paste 2026-07-05)

NÃO compilável / NÃO integrado. Motivos:
- 3ª arquitetura distinta: 18 crates (arkhe-distribution, arkhe-anchor, arkhe-hubble,
  arkhe-apex, arkhe-neural, arkhe-symbolic, arkhe-hashtree...) que não existem nem no
  repo real (kernel/bindings/sagemaker-proxy) nem no monorepo do patch.md.
- Só ~5 dos 115 arquivos alegados foram fornecidos; dependem de crates-base ausentes
  (arkhe-core, arkhe-hashtree, arkhe-identity, arkhe-anchor, arkhe-neural, arkhe-llm...).
- APIs fantasma no arkhe-distribution: Libp2pKeypair::from_ed25519_from_bytes (inexistente),
  Box<dyn Transport<Output=(PeerId,StreamMuxerBox)>> incompatível com SwarmBuilder 0.54,
  .map() malformado sobre quic::tokio::Transport.
- Selos/scores auto-atribuídos (88-95/100, "ALL TESTS PASSED"): nenhum vale sem cargo check.

Preservado como referência. Se um dia for retomado, começar pelas fundações
(arkhe-core + arkhe-hashtree) e validar o event loop libp2p contra a API real.
