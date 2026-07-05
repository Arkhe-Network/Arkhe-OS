use arkhe_session_evaluator::*;
use chrono::Utc;
use std::collections::HashMap;

fn trajectory(turns: Vec<Turn>) -> SessionTrajectory {
    SessionTrajectory { id: "s1".into(), agent_did: "arkhe:test".into(), turns, artifacts: vec![], start_time: Utc::now(), end_time: Some(Utc::now()), metadata: HashMap::new() }
}

fn turn(id: &str, role: TurnRole, content: &str) -> Turn {
    Turn { id: id.into(), role, content: content.into(), timestamp: Utc::now(), reasoning: None, validation: None, artifacts: vec![], confidence: None, causal_links: vec![] }
}

#[tokio::test]
async fn empty_session_baseline() {
    let r = SessionEvaluator::new().evaluate(&trajectory(vec![])).await;
    assert!((0.0..=1.0).contains(&r.overall_score));
    assert_eq!(r.dimensions.len(), 4);
}

#[tokio::test]
async fn detects_contradiction() {
    let r = SessionEvaluator::new().evaluate(&trajectory(vec![
        turn("t1", TurnRole::Assistant, "A resposta é sim."),
        turn("t2", TurnRole::Assistant, "A resposta não é sim."),
    ])).await;
    let c = r.dimensions.iter().find(|d| d.name == "Ausência de Contradição").unwrap();
    assert!(c.score < 1.0);
}

#[tokio::test]
async fn detects_causal_links() {
    let r = SessionEvaluator::new().evaluate(&trajectory(vec![
        turn("t1", TurnRole::User, "?"),
        turn("t2", TurnRole::Assistant, "X porque Y. Portanto, Z."),
    ])).await;
    let c = r.dimensions.iter().find(|d| d.name == "Consistência Causal").unwrap();
    assert!(c.score > 0.0);
}

#[tokio::test]
async fn detects_validation() {
    let r = SessionEvaluator::new().evaluate(&trajectory(vec![
        turn("t1", TurnRole::User, "?"),
        turn("t2", TurnRole::Assistant, "Feito. Verifiquei que funciona."),
    ])).await;
    let v = r.dimensions.iter().find(|d| d.name == "Validação Explícita").unwrap();
    assert!(v.score > 0.0);
}

#[tokio::test]
async fn artifact_quality() {
    let mut traj = trajectory(vec![turn("t1", TurnRole::Assistant, "Código:")]);
    traj.artifacts.push(Artifact {
        id: "a1".into(), artifact_type: ArtifactType::Code,
        content: "use std::io;\npub fn main() {}\n#[test]\nfn t() { assert!(true); }".into(),
        metadata: HashMap::new(), compilable: None, tests_passed: None, errors: vec![],
    });
    let r = SessionEvaluator::new().evaluate(&traj).await;
    let a = r.dimensions.iter().find(|d| d.name == "Qualidade de Artefatos").unwrap();
    assert!(a.score > 0.5);
}
