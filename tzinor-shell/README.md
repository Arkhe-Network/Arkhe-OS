# 🜏 Tzinor Shell

**Phase-aware interactive shell for Arkhe(L) Ontological Automation Platform**

## Overview

Tzinor Shell is a custom shell implementation for interacting with the Tzinor protocol, Q-MCP quantum mesh network, and phase-coherent system operations. It provides a command-line interface synchronized to the Voyager-1LD cosmic metronome.

## Features

- **Phase-aware commands** synchronized to Voyager-1 frequency (5.787 μHz)
- **Tzinor channel management** for retrocausal communication
- **Q-MCP network interaction** with Hilbert curve topology
- **Hilbert mesh visualization** (3D ASCII rendering)
- **Bell measurement simulation** with post-selection
- **Faxion pulse injection** for phase correction

## Installation

```bash
# Build from source
cargo build --release

# Run
./target/release/tzinor-shell
```

## Commands

### Phase & Clock
| Command | Description |
|---------|-------------|
| `phase` | Display current Voyager phase |
| `clock` | Show detailed clock information |
| `voyager` | Voyager mission status |
| `genesis` | Bitcoin Genesis Block info |

### Tzinor Protocol
| Command | Description |
|---------|-------------|
| `tzinor` | Tzinor channel status |
| `open <past> <future>` | Open Tzinor channel |
| `close` | Close Tzinor channel |
| `inject [phase] [amplitude]` | Inject faxion pulse |
| `measure` | Measure past state |
| `bell` | Perform Bell measurement |

### Q-Mesh Network
| Command | Description |
|---------|-------------|
| `qmesh` | Q-Mesh network status |
| `hilbert [order] [connected]` | Hilbert curve visualization |

### Diagnostics
| Command | Description |
|---------|-------------|
| `coherence [value]` | Display/update coherence metrics |
| `mode <mode>` | Set shell mode (normal/retrocausal/phaselocked/diagnostic) |
| `status` | Full system status |

## Architecture

```
tzinor-shell/
├── src/
│   ├── main.rs           # Entry point
│   ├── shell.rs          # REPL implementation
│   ├── commands.rs       # Built-in commands
│   ├── phase.rs         # Voyager-1LD clock
│   ├── tzinor.rs        # Tzinor protocol
│   ├── qmcp.rs          # Q-MCP network
│   └── hilbert.rs       # Hilbert curve
└── Cargo.toml
```

## Physical Constants

| Constant | Value |
|----------|-------|
| Speed of Light | 299,792,458 m/s |
| 1 Light-Day | 2.59×10¹³ m |
| Resonance Frequency | 5.787 μHz |
| Phase/Day | π rad |

## Usage Example

```bash
$ tzinor-shell

🜏 Tzinor Shell v0.1.0

🜏 [tzinor] Δφ=45.23° Ω=1.0000> phase
Current Phase: 0.789 rad (45.23°)

🜏 [tzinor] Δφ=45.23° Ω=1.0000> open past future
Opening Tzinor channel...
✅ Channel opened

🜏 [tzinor] Δφ=45.23° Ω=1.0000> bell
Bell Measurement: |00⟩ (canonical)
```

## License

MIT
