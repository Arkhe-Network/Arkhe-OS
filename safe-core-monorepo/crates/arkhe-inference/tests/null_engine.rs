use arkhe_inference::*;

#[tokio::test]
async fn null_echoes_input() {
    let engine = NullEngine::new(ModelId::new("test", "null"));
    let req = InferenceRequest::simple("hello");
    let resp = engine.complete(req).await.unwrap();
    assert!(resp.content.contains("hello"));
    assert_eq!(resp.finish_reason, FinishReason::Stop);
    assert!(!resp.usage.is_zero());
}

#[tokio::test]
async fn null_streams_words() {
    let engine = NullEngine::new(ModelId::new("test", "null"));
    let req = InferenceRequest::simple("one two three");
    let mut rx = engine.stream(req).await.unwrap();
    let mut chunks = Vec::new();
    while let Some(c) = rx.recv().await { chunks.push(c.token); }
    assert!(chunks.len() >= 3);
}

#[test]
fn request_constructors() {
    let s = InferenceRequest::simple("x");
    assert_eq!(s.messages.len(), 1);

    let w = InferenceRequest::with_system("sys", "usr");
    assert_eq!(w.messages.len(), 2);
}

#[test]
fn token_usage_arithmetic() {
    let a = TokenUsage::new(10, 5);
    assert_eq!(a.total_tokens, 15);
    assert!(!a.is_zero());

    let z = TokenUsage::default();
    assert!(z.is_zero());

    let sum = a.add(&a);
    assert_eq!(sum.prompt_tokens, 20);
}
