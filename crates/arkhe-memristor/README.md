# 🏛️ arkhe-memristor

**Driver Rust para memristor Ag/(PEA)₂(MA)Pb₂I₇/Ag-synDNA/Pt**

[![License](https://img.shields.io/badge/license-MIT%2FApache--2.0-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.75%2B-orange.svg)](https://rust-lang.org)

---

## 📦 Visão Geral

Este crate fornece um driver para o memristor de ultra-baixa tensão baseado em DNA-perovskite, com as seguintes características:

- **Tensão de operação**: < 0.1 V (VSET ≈ 0.10 V, VRESET ≈ 0.08 V)
- **Potência**: 17 µW (CC = 100 µA), 0.01 W/cm² (CC = 1 mA)
- **ON/OFF ratio**: > 10⁵
- **Endurance**: > 10³ ciclos
- **Retenção**: > 4 × 10³ s
- **Estabilidade ambiente**: > 6 semanas
- **Temperatura**: até 393 K (120°C)

## 🚀 Quick Start

```rust
use arkhe_memristor::{MemristorDriver, Memristor};

let mut mem = MemristorDriver::new();
mem.set_voltage(0.09).unwrap();
mem.set_compliance_current(100e-6).unwrap();

mem.set(None).unwrap();
println!("State: {:?}", mem.read().unwrap());

mem.reset(None).unwrap();
println!("State: {:?}", mem.read().unwrap());
```

## 📊 Métricas

```rust
let metrics = mem.metrics();
let power = metrics.power_metrics();
println!("SET power: {:.2} µW", power.set_power_mw * 1000.0);
```

## 🧪 Testes

```bash
cargo test
```

## 📄 Licença

MIT OR Apache-2.0
