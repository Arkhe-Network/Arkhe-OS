use arkhe_agi::AgiCoordinator;
use arkhe_inference::{NullEngine, InferenceEngine, ModelId};

#[tokio::test]
async fn coordinator_processes_input() {
    let engine = Arc::new(NullEngine::new(ModelId::new("test", "null")));
    let coordinator = AgiCoordinator::new(engine, "test-session");

    let response = coordinator.process("O que é soberania digital?").await.unwrap();
    assert!(!response.is_empty());
    assert!(response.contains("soberania digital"));
}

#[tokio::test]
async fn coordinator_tracks_session_id() {
    let engine = Arc::new(NullEngine::new(ModelId::new("test", "null")));
    let coordinator = AgiCoordinator::new(engine, "my-session-123");

    assert_eq!(coordinator.session_id(), "my-session-123");
}

use std::sync::Arc;
