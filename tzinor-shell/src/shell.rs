//! Tzinor Shell Core
//!
//! Interactive shell implementation with phase-aware command processing.

use anyhow::Result;
use rustyline::{Config, DefaultEditor};

use crate::commands::CommandRegistry;
use crate::phase::VoyagerClock;
use crate::tzinor::TzinorChannel;

pub struct TzinorShell {
    editor: DefaultEditor,
    registry: CommandRegistry,
    voyager_clock: VoyagerClock,
    tzinor_channel: TzinorChannel,
    history_path: String,
    prompt_template: String,
    coherence: f64,
    mode: ShellMode,
}

#[derive(Debug, Clone, PartialEq)]
pub enum ShellMode {
    Normal,
    Retrocausal,
    PhaseLocked,
    Diagnostic,
}

impl TzinorShell {
    pub fn new() -> Result<Self> {
        let config = Config::builder().history_ignore_dups(true)?;
        let config = config.build();

        let editor = DefaultEditor::with_config(config)?;

        let history_path = dirs::data_local_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join("tzinor-shell")
            .join("history");

        std::fs::create_dir_all(&history_path)?;

        let mut shell = Self {
            editor,
            registry: CommandRegistry::new(),
            voyager_clock: VoyagerClock::new()?,
            tzinor_channel: TzinorChannel::new(),
            history_path: history_path.to_string_lossy().to_string(),
            prompt_template: String::from("🜏 [tzinor] Δφ={phase} Ω={coherence}> "),
            coherence: 1.0,
            mode: ShellMode::Normal,
        };

        shell.load_history()?;
        shell.register_builtins();

        Ok(shell)
    }

    fn register_builtins(&mut self) {
        self.registry.register("help", crate::commands::help_cmd);
        self.registry.register("phase", crate::commands::phase_cmd);
        self.registry.register("clock", crate::commands::clock_cmd);
        self.registry
            .register("tzinor", crate::commands::tzinor_cmd);
        self.registry.register("qmesh", crate::commands::qmesh_cmd);
        self.registry
            .register("hilbert", crate::commands::hilbert_cmd);
        self.registry
            .register("coherence", crate::commands::coherence_cmd);
        self.registry
            .register("inject", crate::commands::inject_cmd);
        self.registry
            .register("measure", crate::commands::measure_cmd);
        self.registry.register("bell", crate::commands::bell_cmd);
        self.registry.register("open", crate::commands::open_cmd);
        self.registry.register("close", crate::commands::close_cmd);
        self.registry
            .register("status", crate::commands::status_cmd);
        self.registry.register("clear", crate::commands::clear_cmd);
        self.registry.register("exit", crate::commands::exit_cmd);
        self.registry.register("mode", crate::commands::mode_cmd);
        self.registry
            .register("genesis", crate::commands::genesis_cmd);
        self.registry
            .register("voyager", crate::commands::voyager_cmd);
        self.registry.register("rlm", crate::commands::rlm_cmd);
        self.registry
            .register("rlm-qmesh", crate::commands::rlm_qmesh_cmd);
        self.registry
            .register("rlm-phase", crate::commands::rlm_phase_cmd);
        self.registry
            .register("rlm-tzinor", crate::commands::rlm_tzinor_cmd);
        self.registry
            .register("rlm-sandbox", crate::commands::rlm_sandbox_cmd);
        self.registry
            .register("rlm-query", crate::commands::rlm_query_cmd);
    }

    fn load_history(&mut self) -> Result<()> {
        let history_file = std::path::Path::new(&self.history_path).join("history.txt");
        if history_file.exists() {
            self.editor.load_history(&history_file)?;
        }
        Ok(())
    }

    fn save_history(&mut self) -> Result<()> {
        let history_file = std::path::Path::new(&self.history_path).join("history.txt");
        self.editor.save_history(&history_file)?;
        Ok(())
    }

    fn generate_prompt(&self) -> String {
        let phase = self.voyager_clock.current_phase_degrees();
        let coherence = self.coherence;
        let mode_indicator = match self.mode {
            ShellMode::Normal => "",
            ShellMode::Retrocausal => "[RETRO] ",
            ShellMode::PhaseLocked => "[PLL] ",
            ShellMode::Diagnostic => "[DIAG] ",
        };

        format!("🜏 {}Δφ={:.2}° Ω={:.4}> ", mode_indicator, phase, coherence)
    }

    pub fn run(&mut self) -> Result<()> {
        println!("╔══════════════════════════════════════════════════════════════════════╗");
        println!("║  🜏 TZINOR SHELL v0.1.0 - ARKHE(L) ONTOLOGICAL AUTOMATION PLATFORM ║");
        println!("║  Phase-aware command interface. Type 'help' for available commands.     ║");
        println!("╚══════════════════════════════════════════════════════════════════════╝");
        println!();

        loop {
            let prompt = self.generate_prompt();

            match self.editor.readline(&prompt) {
                Ok(line) => {
                    let line = line.trim();
                    if line.is_empty() {
                        continue;
                    }

                    self.editor.add_history_entry(line)?;

                    if let Err(e) = self.execute_line(line) {
                        eprintln!("Error: {}", e);
                    }

                    self.save_history()?;
                }
                Err(rustyline::error::ReadlineError::Interrupted) => {
                    println!("^C");
                    continue;
                }
                Err(rustyline::error::ReadlineError::Eof) => {
                    println!("\n🜏 Exiting Tzinor Shell. The phase persists.");
                    break;
                }
                Err(e) => {
                    eprintln!("Error: {}", e);
                    break;
                }
            }
        }

        Ok(())
    }

    fn execute_line(&mut self, line: &str) -> Result<()> {
        let parts: Vec<&str> = line.split_whitespace().collect();

        if parts.is_empty() {
            return Ok(());
        }

        let cmd = parts[0];
        let args = &parts[1..];

        match cmd {
            "exit" | "quit" | "q" => {
                crate::commands::exit_cmd(args, self)?;
                std::process::exit(0);
            }
            "clear" | "cls" => {
                print!("\x1B[2J\x1B[H");
                Ok(())
            }
            "help" | "?" => crate::commands::help_cmd(args, self),
            _ => {
                if let Some(handler) = self.registry.get(cmd) {
                    handler(args, self)
                } else {
                    Err(anyhow::anyhow!(
                        "Unknown command: {}. Type 'help' for available commands.",
                        cmd
                    ))
                }
            }
        }
    }

    pub fn voyager_clock_mut(&mut self) -> &mut VoyagerClock {
        &mut self.voyager_clock
    }

    pub fn tzinor_channel_mut(&mut self) -> &mut TzinorChannel {
        &mut self.tzinor_channel
    }

    pub fn coherence(&self) -> f64 {
        self.coherence
    }

    pub fn set_coherence(&mut self, coherence: f64) {
        self.coherence = coherence.clamp(0.0, 1.0);
    }

    pub fn mode(&self) -> ShellMode {
        self.mode.clone()
    }

    pub fn set_mode(&mut self, mode: ShellMode) {
        self.mode = mode;
    }
}
