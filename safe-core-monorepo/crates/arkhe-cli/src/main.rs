use clap::Parser;

#[derive(Parser, Debug)]
#[command(name = "arkhe", version, about = "Arkhe OS — Sistema Operacional de Soberania Digital")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(clap::Subcommand, Debug)]
enum Commands {
    Chat { #[arg(long, default_value = "null/null")] model: String },
    Evaluate { #[arg(long)] session: String },
    Info,
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env().add_directive("arkhe=info".parse().unwrap()))
        .init();

    match Cli::parse().command {
        Commands::Chat { model } => println!("🏛️ Arkhe Chat (modelo: {})", model),
        Commands::Evaluate { session } => println!("🏛️ Avaliando sessão: {}", session),
        Commands::Info => println!("🏛️ Arkhe OS v{} — 11 crates", env!("CARGO_PKG_VERSION")),
    }
}
