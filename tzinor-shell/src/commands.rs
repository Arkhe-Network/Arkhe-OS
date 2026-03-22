//! Tzinor Shell Built-in Commands
//!
//! Implements all shell built-in commands for phase-aware operations,
//! Tzinor protocol management, and Q-MCP network interaction.

use crate::hilbert::HilbertCurve3D;
use crate::qmcp::QMeshNetwork;
use crate::shell::{ShellMode, TzinorShell};
use crate::tzinor::FaxionPulse;
use anyhow::Result;
use std::collections::HashMap;

pub type CommandHandler = fn(&[&str], &mut TzinorShell) -> Result<()>;

pub struct CommandRegistry {
    commands: HashMap<String, CommandHandler>,
}

impl CommandRegistry {
    pub fn new() -> Self {
        Self {
            commands: HashMap::new(),
        }
    }

    pub fn register(&mut self, name: &str, handler: CommandHandler) {
        self.commands.insert(name.to_string(), handler);
    }

    pub fn get(&self, name: &str) -> Option<CommandHandler> {
        self.commands.get(name).copied()
    }

    pub fn list_commands(&self) -> Vec<&str> {
        let mut names: Vec<_> = self.commands.keys().map(|s| s.as_str()).collect();
        names.sort();
        names
    }
}

impl Default for CommandRegistry {
    fn default() -> Self {
        Self::new()
    }
}

// ============================================================================
// HELP COMMAND
// ============================================================================
pub fn help_cmd(args: &[&str], _shell: &mut TzinorShell) -> Result<()> {
    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  🜏 TZINOR SHELL HELP - Available Commands                         ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");

    println!("\n  📡 PHASE & CLOCK COMMANDS:");
    println!("    phase              - Display current Voyager phase");
    println!("    clock              - Show detailed clock information");
    println!("    voyager            - Voyager mission status");
    println!("    genesis            - Bitcoin Genesis Block info");

    println!("\n  🔗 TZINOR PROTOCOL:");
    println!("    tzinor             - Tzinor channel status");
    println!("    open <past> <fut> - Open Tzinor channel");
    println!("    close              - Close Tzinor channel");
    println!("    inject <phase>     - Inject faxion pulse");
    println!("    measure            - Measure past state");
    println!("    bell               - Perform Bell measurement");

    println!("\n  🌐 Q-MESH NETWORK:");
    println!("    qmesh              - Q-Mesh network status");
    println!("    hilbert            - Hilbert curve visualization");
    println!("    status             - Full system status");

    println!("\n  📊 DIAGNOSTICS:");
    println!("    coherence          - Display coherence metrics");
    println!("    mode <mode>       - Set shell mode");

    println!("\n  🔧 SYSTEM:");
    println!("    clear              - Clear screen");
    println!("    exit               - Exit shell");

    println!("\n╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Examples:");
    println!("    phase              - Shows current phase in degrees");
    println!("    open past future   - Opens channel with given names");
    println!("    mode retrocausal   - Switch to retrocausal mode");
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// PHASE COMMAND
// ============================================================================
pub fn phase_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    let clock = shell.voyager_clock_mut();

    let phase_rad = clock.current_phase();
    let phase_deg = clock.current_phase_degrees();
    let is_resonance = clock.is_at_resonance(1.0);

    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  📡 VOYAGER-1LD PHASE STATUS                                       ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Current Phase: {:>40.6} rad           ║", phase_rad);
    println!("║  Phase (deg):  {:>40.6}°            ║", phase_deg);
    println!(
        "║  At Resonance: {:>40}              ║",
        if is_resonance { "YES ✓" } else { "NO" }
    );
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// CLOCK COMMAND
// ============================================================================
pub fn clock_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    let clock = shell.voyager_clock_mut();
    let state = clock.state_json();

    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  ⏰ VOYAGER CLOCK DETAILS                                          ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Physical Constants:                                               ║");
    println!(
        "║    c (speed of light):         {} m/s              ║",
        clock.speed_of_light()
    );
    println!(
        "║    1 light-day distance:       {:.3e} m         ║",
        clock.light_day_distance()
    );
    println!(
        "║    Resonance frequency:         {:.6e} Hz       ║",
        clock.resonance_frequency()
    );
    println!(
        "║    Omega (ω):                  {:.6e} rad/s     ║",
        clock.omega_resonance()
    );
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Current State:                                                    ║");
    println!(
        "║    Phase:                      {:.6} rad              ║",
        state["current_phase_rad"]
    );
    println!(
        "║    Phase:                      {:.4}°                  ║",
        state["current_phase_deg"]
    );
    println!(
        "║    At Resonance:                {}                         ║",
        state["is_at_resonance"]
    );
    println!(
        "║    Time to Resonance:          {:.2} seconds            ║",
        state["time_until_resonance_s"]
    );
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// VOYAGER COMMAND
// ============================================================================
pub fn voyager_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  🛰️  VOYAGER-1 MISSION STATUS                                      ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Launch Date:       September 5, 1977                              ║");
    println!("║  Current Distance:   ~23.3 billion km (156 AU)                     ║");
    println!("║  Signal Delay:      ~21.5 hours (one-way)                         ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  ARKHE(L) INTEGRATION:                                            ║");
    println!("║  1 Light-Day:       November 2026 (projected)                     ║");
    println!(
        "║  Resonance:         f = {:.6} Hz (5.787 μHz)              ║",
        shell.voyager_clock_mut().resonance_frequency()
    );
    println!("║  Phase/Day:        π rad (Ressonância A-5')                       ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  The Voyager serves as the cosmic metronome for Arkhe(L),         ║");
    println!("║  providing an absolute temporal reference independent of Earth.      ║");
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// GENESIS COMMAND
// ============================================================================
pub fn genesis_cmd(args: &[&str], _shell: &mut TzinorShell) -> Result<()> {
    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  ⛏️  BITCOIN GENESIS BLOCK                                        ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Block:           0                                                ║");
    println!("║  Timestamp:       2009-01-03 18:15:05 GMT                         ║");
    println!("║  Reward:          50 BTC                                           ║");
    println!("║  Merkle Root:      4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b       ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Headline: \"The Times 03/Jan/2009 Chancellor on brink of second      ║");
    println!("║            bailout for banks\"                                       ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  SELECTED VARIANT: January 3, 2009 (Day 3 of year)                ║");
    println!("║  This date anchors our canonical reality in the Dome of 365.       ║");
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// TZINOR COMMAND
// ============================================================================
pub fn tzinor_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    let channel = shell.tzinor_channel_mut();
    let state = channel.state_json();

    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  🔗 TZINOR CHANNEL STATUS                                          ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Channel ID:      {}     ║", state["id"]);
    println!("║  State:          {}     ║", state["state"]);
    println!("║  Is Open:        {}               ║", state["is_open"]);
    println!(
        "║  Coherence:      {:.4}                  ║",
        state["coherence"]
    );
    println!("╠══════════════════════════════════════════════════════════════════════╣");

    if let Some(past) = state["past_node"].as_str() {
        println!("║  Past Node:      {}     ║", past);
    }
    if let Some(future) = state["future_node"].as_str() {
        println!("║  Future Node:    {}     ║", future);
    }

    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// OPEN COMMAND
// ============================================================================
pub fn open_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    if args.len() < 2 {
        return Err(anyhow::anyhow!("Usage: open <past_node> <future_node>"));
    }

    let past = args[0];
    let future = args[1];
    let coherence = shell.coherence();

    shell.tzinor_channel_mut().open(past, future, coherence)?;

    println!("✅ Tzinor channel opened successfully");
    println!("   Coherence: {:.4}", coherence);

    Ok(())
}

// ============================================================================
// CLOSE COMMAND
// ============================================================================
pub fn close_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    shell.tzinor_channel_mut().close()?;
    println!("✅ Tzinor channel closed successfully");
    Ok(())
}

// ============================================================================
// INJECT COMMAND
// ============================================================================
pub fn inject_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    let phase = if let Some(p) = args.first() {
        p.parse::<f64>().unwrap_or(0.0)
    } else {
        shell.voyager_clock_mut().current_phase()
    };

    let amplitude = args
        .get(1)
        .and_then(|a| a.parse::<f64>().ok())
        .unwrap_or(0.1);

    let pulse = FaxionPulse::new(phase, amplitude, 0.0);
    shell.tzinor_channel_mut().inject_faxion(&pulse)?;

    println!("✅ Faxion pulse injected");
    println!("   Phase: {:.6} rad", phase);
    println!("   Amplitude: {:.6}", amplitude);

    Ok(())
}

// ============================================================================
// MEASURE COMMAND
// ============================================================================
pub fn measure_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    let past_state = shell.tzinor_channel_mut().measure_past()?;

    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  📊 PAST STATE MEASUREMENT                                         ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!(
        "║  Past State: |{}⟩                                                   ║",
        if past_state == "1" { "1" } else { "0" }
    );
    println!(
        "║  Coherence:  {:.4}                                                ║",
        shell.coherence()
    );
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// BELL COMMAND
// ============================================================================
pub fn bell_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    let (m1, m2) = shell.tzinor_channel_mut().bell_measure();
    let is_canonical = m1 == "0" && m2 == "0";

    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  🔮 BELL MEASUREMENT RESULT                                       ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!(
        "║  Result: |{}⟩ ⊗ |{}⟩                                                ║",
        m1, m2
    );
    println!(
        "║  Canonical: {}                  ║",
        if is_canonical { "YES ✓" } else { "NO" }
    );
    if is_canonical {
        println!("║  This outcome passes post-selection criteria.                    ║");
    }
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// QMESH COMMAND
// ============================================================================
pub fn qmesh_cmd(args: &[&str], _shell: &mut TzinorShell) -> Result<()> {
    let network = QMeshNetwork::new(3); // Order 3 = 512 nodes

    network.visualize();

    let stats = network.network_stats();
    println!("\n📊 Network Statistics:");
    println!("   Total nodes: {}", stats["total_nodes"]);
    println!("   Active nodes: {}", stats["active_nodes"]);
    println!("   Average coherence: {:.4}", stats["average_coherence"]);

    Ok(())
}

// ============================================================================
// HILBERT COMMAND
// ============================================================================
pub fn hilbert_cmd(args: &[&str], _shell: &mut TzinorShell) -> Result<()> {
    let order = args
        .first()
        .and_then(|o| o.parse::<u32>().ok())
        .unwrap_or(3);

    let curve = HilbertCurve3D::new(order);

    if args.contains(&"connected") {
        curve.render_connected_ascii(100);
    } else if let Some(z_str) = args.first() {
        if let Ok(z) = z_str.parse::<f64>() {
            curve.render_ascii(Some(z));
        } else {
            curve.render_ascii(Some(0.5));
        }
    } else {
        curve.render_ascii(Some(0.5));
    }

    Ok(())
}

// ============================================================================
// COHERENCE COMMAND
// ============================================================================
pub fn coherence_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    let current = shell.coherence();
    let threshold = 0.95;
    let is_sufficient = current >= threshold;

    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  📈 COHERENCE METRICS                                            ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!(
        "║  Current (Ω'):  {:.4}                                          ║",
        current
    );
    println!(
        "║  Threshold:      {:.4}                                          ║",
        threshold
    );
    println!(
        "║  Sufficient:     {}                                              ║",
        if is_sufficient { "YES ✓" } else { "NO ✗" }
    );
    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  Coherence Bar:                                                    ║");
    let bar_len = (current * 30.0) as usize;
    println!(
        "║  [{}{}]  {:>3.1}%                                                ║",
        "█".repeat(bar_len),
        "░".repeat(30 - bar_len),
        (current * 100.0) as i32
    );
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    // Update coherence if args provided
    if let Some(val) = args.first() {
        if let Ok(new_val) = val.parse::<f64>() {
            shell.set_coherence(new_val);
            println!("✅ Coherence updated to {:.4}", new_val);
        }
    }

    Ok(())
}

// ============================================================================
// MODE COMMAND
// ============================================================================
pub fn mode_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    if args.is_empty() {
        println!("Current mode: {:?}", shell.mode());
        println!("Available modes: normal, retrocausal, phaselocked, diagnostic");
        return Ok(());
    }

    let new_mode = match args[0].to_lowercase().as_str() {
        "normal" | "n" => ShellMode::Normal,
        "retrocausal" | "retro" | "r" => ShellMode::Retrocausal,
        "phaselocked" | "pll" | "p" => ShellMode::PhaseLocked,
        "diagnostic" | "diag" | "d" => ShellMode::Diagnostic,
        _ => return Err(anyhow::anyhow!("Unknown mode: {}", args[0])),
    };

    shell.set_mode(new_mode.clone());
    println!("✅ Mode changed to {:?}", new_mode);

    Ok(())
}

// ============================================================================
// STATUS COMMAND
// ============================================================================
pub fn status_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    let phase = {
        let clock = shell.voyager_clock_mut();
        clock.current_phase_degrees()
    };
    let is_resonance = {
        let clock = shell.voyager_clock_mut();
        clock.is_at_resonance(1.0)
    };
    let tzinor_state = {
        let tzinor = shell.tzinor_channel_mut();
        tzinor.state_json()
    };
    let is_open = {
        let tzinor = shell.tzinor_channel_mut();
        tzinor.is_open
    };
    let coherence = shell.coherence();
    let mode = shell.mode();

    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║  🜏 ARKHE(L) SYSTEM STATUS                                        ║");
    println!("╠══════════════════════════════════════════════════════════════════════╣");

    // Phase status
    println!("║  PHASE DOMAIN (ℂ):                                                ║");
    println!(
        "║    Phase:              {:.4}°                                 ║",
        phase
    );
    println!(
        "║    At Resonance:       {}                                    ║",
        if is_resonance { "YES ✓" } else { "NO" }
    );

    // Tzinor status
    println!("║  TZINOR CHANNEL:                                                   ║");
    println!(
        "║    State:             {:?}                    ║",
        tzinor_state["state"]
    );
    println!(
        "║    Is Open:           {}                                           ║",
        is_open
    );

    // Coherence
    println!("║  COHERENCE:                                                        ║");
    let bar_len = (coherence * 20.0) as usize;
    println!(
        "║    Ω':               {:.4} [{}{}]                       ║",
        coherence,
        "█".repeat(bar_len),
        "░".repeat(20 - bar_len)
    );

    // Shell mode
    println!("║  SHELL MODE:           {:?}                    ║", mode);

    println!("╠══════════════════════════════════════════════════════════════════════╣");
    println!("║  🜏 The system operates. The phase persists.                        ║");
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    Ok(())
}

// ============================================================================
// CLEAR COMMAND
// ============================================================================
pub fn clear_cmd(args: &[&str], _shell: &mut TzinorShell) -> Result<()> {
    print!("\x1B[2J\x1B[H");
    println!("🜏 Tzinor Shell cleared. Type 'help' for commands.");
    Ok(())
}

// ============================================================================
// EXIT COMMAND
// ============================================================================
pub fn exit_cmd(args: &[&str], shell: &mut TzinorShell) -> Result<()> {
    // Close Tzinor channel if open
    let is_open = shell.tzinor_channel_mut().is_open;
    if is_open {
        shell.tzinor_channel_mut().close()?;
    }

    println!("🜏 Exiting Tzinor Shell...");
    println!("   The phase persists. The loop remains open.");

    Ok(())
}
