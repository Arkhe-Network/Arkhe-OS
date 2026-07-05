use arkhe_agi::{AgiCoordinator, SessionHistory};
use arkhe_core::{AlwaysAllowVerifier, InMemoryAgentMemory};
use arkhe_inference::{NullEngine, ModelId, InferenceEngine};
use arkhe_session_evaluator::SessionEvaluator;
use arkhe_reflector_agent::ReflectorAgent;
use std::sync::Arc;

#[tokio::test]
async fn coordinator_process_works() {
    let safety = Arc::new(AlwaysAllowVerifier);
    let memory = Arc::new(InMemoryAgentMemory::new());
    let inference = Arc::new(NullEngine::new(ModelId::new("test", "null")));
    let evaluator = Arc::new(SessionEvaluator::new());

    let coord = AgiCoordinator::new(
        safety, memory, inference, evaluator, "test-session", "You are helpful.",
    );

    let resp = coord.process("O que é soberania digital?").await.unwrap();
    assert!(!resp.is_empty());
    assert!(resp.contains("soberania digital"));

    // Segundo turno deve funcionar (histórico)
    let resp2 = coord.process("Pode detalhar?").await.unwrap();
    assert!(!resp2.is_empty());

    // Stats
    let (sid, turns, usage) = coord.stats().await;
    assert_eq!(sid, "test-session");
    assert_eq!(turns, 2);
    assert!(!usage.is_zero());
}

#[tokio::test]
async fn coordinator_safety_blocks() {
    use arkhe_core::AlwaysRejectVerifier;
    let safety = Arc::new(AlwaysRejectVerifier { reason: "blocked".into() });
    let memory = Arc::new(InMemoryAgentMemory::new());
    let inference = Arc::new(NullEngine::new(ModelId::new("test", "null")));
    let evaluator = Arc::new(SessionEvaluator::new());

    let coord = AgiCoordinator::new(safety, memory, inference, evaluator, "blocked-session", "sys");

    let result = coord.process("test").await;
    assert!(result.is_err());
}

#[tokio::test]
async fn coordinator_evaluate_session() {
    let safety = Arc::new(AlwaysAllowVerifier);
    let memory = Arc::new(InMemoryAgentMemory::new());
    let inference = Arc::new(NullEngine::new(ModelId::new("test", "null")));
    let evaluator = Arc::new(SessionEvaluator::new());

    let coord = AgiCoordinator::new(safety, memory, inference, evaluator, "eval-session", "sys");

    coord.process("X porque Y. Portanto, Z.").await.unwrap();
    coord.process("Verifiquei que W é verdadeiro.").await.unwrap();

    let result = coord.evaluate_session().await.unwrap();
    assert!((0.0..=1.0).contains(&result.overall_score));
    assert_eq!(result.dimensions.len(), 4);
}

#[test]
fn session_history_works() {
    let mut h = SessionHistory::new("test");
    assert_eq!(h.turn_count(), 0);

    h.push_turn("hello", "world", arkhe_inference::TokenUsage::new(5, 3));
    assert_eq!(h.turn_count(), 1);
    assert_eq!(h.total_usage().total_tokens, 8);
    assert_eq!(h.messages().len(), 2);

    let v = h.to_vec();
    assert_eq!(v.len(), 2);

    h.clear();
    assert_eq!(h.turn_count(), 0);
    assert!(h.total_usage().is_zero());
}
