use clap::{Parser, Subcommand};
use std::process::Command;

#[derive(Parser)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    PreCommit,
    Ci,
    FullAudit,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::PreCommit => pre_commit()?,
        Commands::Ci => ci()?,
        Commands::FullAudit => full_audit()?,
    }
    Ok(())
}

fn pre_commit() -> anyhow::Result<()> {
    run("cargo fmt --all -- --check")?;
    run("cargo check --workspace --all-targets --all-features")?;
    run("cargo clippy --workspace --all-targets --all-features -- -D warnings")?;
    run("cargo deny --config .config/deny.toml check")?;                           // ✅ unificado
    run("cargo audit --deny-warnings")?;
    run("cargo llvm-cov --workspace --lib --lcov --output-path target/lcov-unit.info")?;
    Ok(())
}

fn ci() -> anyhow::Result<()> {
    pre_commit()?;
    run("cargo test --workspace")?;
    run("cargo semver-checks --workspace --baseline-rev HEAD~1")?;
    run("cargo llvm-cov --workspace --lcov --output-path lcov.info")?;
    run("cargo bench")?;
    run("cargo doc --workspace --no-deps --document-private-items")?;  // ✅ novo
    run("cargo insta test --workspace --unreferenced=auto")?;                     // ✅ novo
    Ok(())
}

fn full_audit() -> anyhow::Result<()> {
    ci()?;
    run("cargo deadlinks")?;
    run("cargo check --workspace --all-targets --all-features --ignore-rust-version")?; // MSRV check
    // Geração de SBOM
    run("cargo sbom")?;
    Ok(())
}

fn run(cmd: &str) -> anyhow::Result<()> {
    let status = Command::new("sh").arg("-c").arg(cmd).status()?;
    if !status.success() {
        anyhow::bail!("Command failed: {}", cmd);
    }
    Ok(())
}
