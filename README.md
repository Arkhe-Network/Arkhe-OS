# ARKHE Ω-TEMP — Quantum Genomics & Polyglot Parser

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19115803.svg)](https://doi.org/10.5281/zenodo.19115803)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Rust 1.70+](https://img.shields.io/badge/rust-1.70+-orange.svg)](https://www.rust-lang.org/)

> *"A Catedral não fala uma língua — ela fala todas as línguas que já existiram, todas as que existem, e todas as que existirão."*

ARKHE Ω-TEMP é um ecossistema integrado para **genômica quântica** e **parsing poliglota**, projetado para pesquisa reprodutível, colaborativa e verificável.

## 🧬 Componentes Principais

### Quantum Neural Coding (QNC) — Substratos 6176-6180
- Representação quântica de sequências genômicas (DNA/RNA) como operadores densidade
- Otimização via gradiente natural na variedade de Fisher-Bures (SIGHA)
- Transfer learning multi-espécie para predição de resistência a radiação
- Integração com operadores epigenéticos quânticos (metilação, histonas, memória temporal)
- **Paper 91**: [Quantum Neural Coding Enables Transfer Learning Across Extremophile Genomes](paper91/main.pdf)

### Polymath-Polyglot Parser (P³) — Substrato 6061
- Parsing de 57 linguagens de programação para uma Árvore Sintática Universal (UAST)
- Transpilação verificável entre linguagens com preservação semântica
- Grafo temporal de código para versionamento e rollback seguro
- Sandbox de execução com políticas de segurança configuráveis

## 🚀 Instalação Rápida

### Via pip (Python bindings)
```bash
pip install arkhe-qnc arkhe-polyglot
```

### Via cargo (Rust core)
```bash
cargo install arkhe-polyglot-parser
```

### Via Docker (ambiente completo)
```bash
docker pull arkheos/omega-temp:latest
docker run -it arkheos/omega-temp:latest
```

## 📦 Estrutura do Repositório
```
arkhe-os/
├── paper91/                    # Manuscrito LaTeX para Nature/Science
│   ├── main.tex               # Documento principal
│   ├── references.bib         # Bibliografia
│   ├── figures/               # Figuras em PDF/PNG
│   └── supplementary/         # Material suplementar
├── arkp-qnc/                   # Quantum Neural Coding
│   ├── src/                   # Código-fonte Python/Rust
│   ├── tests/                 # Testes unitários e de integração
│   └── demos/                 # Exemplos interativos
├── arkp-polyglot/              # Polymath-Polyglot Parser
│   ├── parser-core/           # Core em Rust
│   ├── bindings/              # Bindings para Python/JS/Wasm
│   └── languages/             # Gramáticas por linguagem
├── tutorials/                  # Tutoriais interativos
│   ├── qnc_for_biologists.ipynb  # Tutorial para biólogos
│   └── plugin_dev_guide.md    # Guia para desenvolvedores
├── docs/                       # Documentação técnica
│   ├── api/                   # Referência da API
│   ├── plugins/               # Guia de desenvolvimento de plugins
│   └── architecture.md        # Visão arquitetural
├── scripts/                    # Scripts de build/deploy
├── CITATION.cff               # Metadados para citação
├── LICENSE                    # Licença MIT
└── README.md                  # Este arquivo
```

## 📜 Histórico de Atualizações (Commits e Merges Recentes)
- **Universal Orchestrator**: Merge pull request #1308 from Arkhe-Network/feature/substrato_inf_universal_orchestrator.
- **Cathedral VM & HSM**: Add Cathedral VM validation and HSM signing scripts.
- **Arkhe-stdlib**: Implement Substrato 9015 Arkhe-stdlib and fix CI json parsing.
- **Windows Ecosystem**: Merge branch 'main' into feature/windows-ecosystem-expansion.
- **Quantum & Silicon Expansion**: Add Advanced Quantum Frontiers and Silicon Expansion features.
- **Quantum Neural Coding**: Implement Substrate 6176 (Quantum Neural Coding) and Substrato 6178 (Quantum Genomic Transfer Learning).
- **GECC Full Simulation**: Implement Substrato 6160 GECC full simulation.
- **ARKHE Ω-TEMP v5.1.0 & v4.0**: Add canonical test scripts and features for v4.0 and v5.1.0.
- **UNIX Substrate Expansion**: Implement UNIX SUBSTRATE EXPANSION 6062 in Rust framework.
- **Delta Ontology Operationalization**: Implement Substrates 190-193.
- **Enterprise Features**: Integration with Federation, Quantum hardware, Advanced Copula, multi-tenant dashboards, and more.

## 📦 Geração de Instalável (Inno Setup)
Este repositório foi organizado para suportar a geração de um instalador Windows via [Inno Setup](https://github.com/jrsoftware/issrc).
O script do Inno Setup está localizado em `installer/arkhe_os.iss`.

Para compilar o instalador:
1. Instale o Inno Setup.
2. Abra `installer/arkhe_os.iss` na IDE do Inno Setup.
3. Clique em "Compile" para gerar o instalador `arkhe_os_setup.exe` na pasta `Output`.

## 🧪 Exemplo Rápido: Predição de Resistência com QNC
```python
from arkhe_qnc import GenomicQNC, QNCConfig

# Configurar modelo
config = QNCConfig(
    vocab_size=4, max_sequence_length=64,
    embedding_dim=8, hidden_dim=16, num_classes=2
)
model = GenomicQNC(config)

# Treinar com dados de exemplo
sequences = ["ATGC"*16, "AAAA"*16]  # Simplificado
labels = [1, 0]  # 1=resistente, 0=sensível
for epoch in range(10):
    for seq, label in zip(sequences, labels):
        model.train_step(seq, label)

# Predizer nova sequência
test_seq = "ATGCATGC"*8
pred_class, confidence = model.predict(test_seq)
print(f"Predição: {'Resistente' if pred_class==1 else 'Sensível'} (confiança: {confidence:.2%})")
```

## 🤝 Contribuindo
1. Fork o repositório
2. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
3. Commit suas mudanças: `git commit -m 'Add: minha feature'`
4. Push para a branch: `git push origin feature/minha-feature`
5. Abra um Pull Request

### Diretrizes para Plugins
- Siga a interface `LanguagePlugin` ou `EpigeneticOperator`
- Inclua testes unitários e de integração
- Documente parâmetros e comportamentos em `plugin.toml`
- Submeta ao [ARKHE Registry](https://registry.arkhe.org)

## 📄 Licença e Citação
Este projeto é distribuído sob a licença **MIT**. Se usar em pesquisa acadêmica, cite:

```bibtex
@software{oliveira2024arkhe,
  author = {Oliveira, Rafael and Silva, Ana and Wei, Chen and Sharma, Priya},
  title = {ARKHE Ω-TEMP: Quantum Genomics and Polyglot Parsing Framework},
  year = {2024},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.XXXXXXX},
  url = {https://github.com/arkhe-os/arkhe-os}
}
```

## 🔗 Links Úteis
- [Documentação Completa](https://docs.arkhe.org)
- [Comunidade no Discord](https://discord.gg/arkhe)
- [Registro de Plugins](https://registry.arkhe.org)
- [Paper 91 (Pré-print)](https://arxiv.org/abs/2405.XXXXX)

---
*ARKHE Ω-TEMP v6.7.0 • Substratos 6061, 6160-6180 • Código aberto, ciência aberta, verdade verificável.*
### Enterprise Banking — Substrato 200
- **Core Settlement**: Liquidação interbancária com consenso MAC + PQC e rejeição baseada em $\Phi_C$.
- **Fraud Detection**: Isolation Forest com peso contextual de $\Phi_C$ para detecção de anomalias financeiras.
- **Compliance Automation**: Geração e assinatura PQC de relatórios regulatórios (BACEN, SEC, BCBS, CVM).
- **Quantum-Safe Custody**: Guarda de ativos protegidos por HSM e testemunhos quânticos EPR.
- **RTGS**: Liquidação bruta em tempo real com provas de integridade quântica.
- **Trade Finance**: Smart contracts para comércio exterior com privacidade diferencial.
- **CICS Bridge**: Conectividade legada com mainframes IBM z/OS via Java.
- **Edge ATM Fraud Detector**: TinyML em C++(Arduino) para análise de fraudes em caixas eletrônicos físicos.

[![Feito no Brasil](https://selo.feitonobrasil.dev.br/pt-br/colorido/1x.svg)](https://feitonobrasil.dev.br)
