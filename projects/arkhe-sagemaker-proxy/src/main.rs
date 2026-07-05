use axum::{
    extract::State,
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::Mutex;
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;
use tracing::info;

#[derive(Clone, Debug, Serialize, Deserialize)]
struct SageMakerRequest {
    model: String,
    input: serde_json::Value,
    params: Option<serde_json::Value>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct SageMakerResponse {
    prediction: serde_json::Value,
    model: String,
    phi_c: f64,
    duration_ms: u64,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct HealthResponse {
    status: String,
    substrate: String,
    version: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct Metrics {
    requests_total: u64,
    errors_total: u64,
    avg_duration_ms: f64,
}

struct AppState {
    metrics: Arc<Mutex<Metrics>>,
}

async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "healthy".into(),
        substrate: "824.2".into(),
        version: "870-G.4.0".into(),
    })
}

async fn ready() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ready".into(),
        substrate: "824.2".into(),
        version: "870-G.4.0".into(),
    })
}

async fn invoke(
    State(state): State<Arc<AppState>>,
    Json(req): Json<SageMakerRequest>,
) -> Result<Json<SageMakerResponse>, StatusCode> {
    let start = std::time::Instant::now();

    let mut metrics = state.metrics.lock().await;
    metrics.requests_total += 1;

    let model_name = req.model.clone();
    let response = SageMakerResponse {
        prediction: serde_json::json!({
            "status": "simulated",
            "model": req.model,
            "phi_c": 0.870,
        }),
        model: model_name.clone(),
        phi_c: 0.870,
        duration_ms: start.elapsed().as_millis() as u64,
    };

    info!("Invoked model {} in {}ms", model_name, response.duration_ms);
    Ok(Json(response))
}

async fn get_metrics(State(state): State<Arc<AppState>>) -> Json<Metrics> {
    let metrics = state.metrics.lock().await;
    Json(metrics.clone())
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter("info,arkhe_sagemaker_proxy=debug")
        .init();

    let state = Arc::new(AppState {
        metrics: Arc::new(Mutex::new(Metrics {
            requests_total: 0,
            errors_total: 0,
            avg_duration_ms: 0.0,
        })),
    });

    let app = Router::new()
        .route("/health", get(health))
        .route("/ready", get(ready))
        .route("/invoke", post(invoke))
        .route("/metrics", get(get_metrics))
        .layer(TraceLayer::new_for_http())
        .layer(CorsLayer::permissive())
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8242").await?;
    info!("ARKHE SageMaker Proxy listening on 0.0.0.0:8242");
    axum::serve(listener, app).await?;

    Ok(())
}
