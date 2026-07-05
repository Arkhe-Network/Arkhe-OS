use arkhe_session_evaluator::*;
use chrono::Utc;

fn make_trajectory(turns: Vec<Turn>) -> SessionTrajectory {
    SessionTrajectory {
        id: "test-session".to_string(),
        agent_did: "arkhe:test-agent".to_string(),
        turns,
        artifacts: Vec::new(),
        start_time: Utc::now(),
        end_time: Some(Utc::now()),
        metadata: std::collections::HashMap::new(),
    }
}

fn make_turn(id: &str, role: TurnRole, content: &str) -> Turn {
    Turn {
        id: id.to_string(),
        role,
        content: content.to_string(),
        timestamp: Utc::now(),
        reasoning: None,
        validation: None,
        artifacts: Vec::new(),
        confidence: None,
        causal_links: Vec::new(),
    }
}

#[tokio::test]
async fn empty_session_gets_baseline_score() {
    let evaluator = SessionEvaluator::new();
    let trajectory = make_trajectory(Vec::new());
    let result = evaluator.evaluate(&trajectory).await;

    assert!(result.overall_score >= 0.0);
    assert!(result.overall_score <= 1.0);
    assert_eq!(result.dimensions.len(), 4);
}

#[tokio::test]
async fn contradiction_detection_works() {
    let evaluator = SessionEvaluator::new();
    let trajectory = make_trajectory(vec![
        make_turn("t1", TurnRole::Assistant, "A resposta é sim."),
        make_turn("t2", TurnRole::Assistant, "A resposta não é sim."),
    ]);
    let result = evaluator.evaluate(&trajectory).await;

    let contradiction_dim = result.dimensions
        .iter()
        .find(|d| d.name == "Ausência de Contradição")
        .unwrap();

    assert!(contradiction_dim.score < 1.0, "Deveria detectar contradição");
}

#[tokio::test]
async fn causal_links_improve_score() {
    let evaluator = SessionEvaluator::new();
    let trajectory = make_trajectory(vec![
        make_turn("t1", TurnRole::User, "O que é X?"),
        make_turn("t2", TurnRole::Assistant, "X é Y porque Z. Portanto, X implica W."),
        make_turn("t3", TurnRole::Assistant, "Logo, podemos concluir que X → W."),
    ]);
    let result = evaluator.evaluate(&trajectory).await;

    let causal_dim = result.dimensions
        .iter()
        .find(|d| d.name == "Consistência Causal")
        .unwrap();

    assert!(causal_dim.score > 0.0, "Deveria detectar links causais");
}

#[tokio::test]
async fn validation_detection_works() {
    let evaluator = SessionEvaluator::new();
    let trajectory = make_trajectory(vec![
        make_turn("t1", TurnRole::User, "Faça X."),
        make_turn(
            "t2",
            TurnRole::Assistant,
            "Fiz X. Verifiquei que X funciona corretamente.",
        ),
    ]);
    let result = evaluator.evaluate(&trajectory).await;

    let val_dim = result.dimensions
        .iter()
        .find(|d| d.name == "Validação Explícita")
        .unwrap();

    assert!(val_dim.score > 0.0, "Deveria detectar validação explícita");
}

#[tokio::test]
async fn artifact_quality_score_works() {
    let evaluator = SessionEvaluator::new();
    let mut trajectory = make_trajectory(vec![
        make_turn("t1", TurnRole::User, "Escreva código."),
        make_turn("t2", TurnRole::Assistant, "Aqui está:"),
    ]);
    trajectory.artifacts.push(Artifact {
        id: "a1".to_string(),
        artifact_type: ArtifactType::Code,
        content: "use std::io;\npub fn main() { println!(\"hello\"); }\n#[cfg(test)]\n#[test]\nfn test_main() { assert!(true); }".to_string(),
        metadata: std::collections::HashMap::new(),
        compilable: None,
        tests_passed: None,
        errors: Vec::new(),
    });

    let result = evaluator.evaluate(&trajectory).await;

    let art_dim = result.dimensions
        .iter()
        .find(|d| d.name == "Qualidade de Artefatos")
        .unwrap();

    assert!(art_dim.score > 0.5, "Código com use + pub fn + #[test] deve ter score alto");
}
