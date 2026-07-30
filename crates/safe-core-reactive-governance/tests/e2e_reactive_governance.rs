use safe_core_reactive_governance::{GovernanceAction, GovernanceEntry, ReactiveLog};

fn setup() -> (Vec<u8>, ReactiveLog) {
    let gov_vk = vec![1, 2, 3];
    let reactive_log = ReactiveLog::new(vec![gov_vk.clone()]);
    (gov_vk, reactive_log)
}

#[tokio::test]
async fn test_reactive_freeze_blocks_operations() {
    let (gov_vk, mut reactive_log) = setup();

    assert!(!reactive_log.is_frozen().await);

    let action = GovernanceAction::EmergencyFreeze {
        reason: "Test freeze".into(),
        duration_seconds: 60,
    };

    let entry = GovernanceEntry {
        action,
        issued_by: "test-authority".into(),
        timestamp: chrono::Utc::now().timestamp(),
        signature: vec![4, 5, 6],
        verifying_key: gov_vk,
    };

    reactive_log.apply_governance_entry(entry).await.unwrap();

    assert!(reactive_log.is_frozen().await, "System should be frozen");
}

#[tokio::test]
async fn test_reactive_ban_routing_path() {
    let (gov_vk, mut reactive_log) = setup();

    assert!(!reactive_log.is_route_banned("router-1", "vision", "dense_v3").await);

    let action = GovernanceAction::BanRoutingPath {
        router_id: "router-1".into(),
        from_module: "vision".into(),
        to_module: "dense_v3".into(),
        reason: "Hallucination risk".into(),
    };

    let entry = GovernanceEntry {
        action,
        issued_by: "test-authority".into(),
        timestamp: chrono::Utc::now().timestamp(),
        signature: vec![4, 5, 6],
        verifying_key: gov_vk,
    };

    reactive_log.apply_governance_entry(entry).await.unwrap();

    assert!(
        reactive_log.is_route_banned("router-1", "vision", "dense_v3").await,
        "Route should be banned"
    );

    assert!(
        !reactive_log.is_route_banned("router-1", "audio", "sparse_v1").await,
        "Unrelated route should be free"
    );
}

#[tokio::test]
async fn test_unauthorized_governance_rejected() {
    let (_gov_vk, mut reactive_log) = setup();

    let attacker_vk = vec![9, 9, 9];

    let action = GovernanceAction::EmergencyFreeze {
        reason: "Malicious freeze".into(),
        duration_seconds: 99999,
    };

    let entry = GovernanceEntry {
        action,
        issued_by: "hacker".into(),
        timestamp: chrono::Utc::now().timestamp(),
        signature: vec![7, 8, 9],
        verifying_key: attacker_vk,
    };

    let result = reactive_log.apply_governance_entry(entry).await;
    assert!(result.is_err());

    assert!(!reactive_log.is_frozen().await);
}
