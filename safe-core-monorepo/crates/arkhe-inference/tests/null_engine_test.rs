use arkhe_inference::{NullEngine, InferenceEngine, ModelId, InferenceRequest};

#[tokio::test]
async fn null_engine_returns_echo() {
    let engine = NullEngine::new(ModelId::new("test", "null"));
    assert!(engine.is_ready());

    let request = InferenceRequest::simple("Olá mundo");
    let response = engine.complete(request).await.unwrap();

    assert!(response.content.contains("Olá mundo"));
    assert_eq!(response.finish_reason, arkhe_inference::FinishReason::Stop);
    assert!(!response.usage.is_zero());
}

#[tokio::test]
async fn null_engine_simple_constructor_works() {
    let request = InferenceRequest::simple("test");
    assert_eq!(request.messages.len(), 1);
    assert_eq!(request.messages[0].content, "test");
}

#[tokio::test]
async fn null_engine_with_system_works() {
    let request = InferenceRequest::with_system("System prompt", "User prompt");
    assert_eq!(request.messages.len(), 2);
}

#[test]
fn token_usage_methods() {
    let a = arkhe_inference::TokenUsage::new(10, 5);
    assert_eq!(a.total_tokens, 15);
    assert!(!a.is_zero());

    let b = arkhe_inference::TokenUsage::new(0, 0);
    assert!(b.is_zero());

    let c = a.add(&b);
    assert_eq!(c.total_tokens, 15);

    let d = a.add(&a);
    assert_eq!(d.prompt_tokens, 20);
}
