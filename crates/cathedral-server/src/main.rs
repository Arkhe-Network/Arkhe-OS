use std::net::SocketAddr;
use std::sync::Arc;
use cathedral_remix_bridge::RemixClient;
use cathedral_wormgraph::WormGraphClient;
use cathedral_zk::ZKGateway;
use cathedral_server::orchestration::Orchestrator;
use cathedral_server::api::create_routes;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();

    let remix = Arc::new(RemixClient::new("http://localhost:3000".to_string()));
    let wormgraph = Arc::new(WormGraphClient::new());
    let zk = Arc::new(ZKGateway::new());

    let orchestrator = Arc::new(Orchestrator::new(remix, wormgraph, zk));

    let app = create_routes(orchestrator);

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    tracing::info!("Listening on {}", addr);
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
