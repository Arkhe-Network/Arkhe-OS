use crate::evidence::{Evidence, EvidenceStatus};
use std::collections::VecDeque;

#[cfg(feature = "http")]
use reqwest::Client;

pub struct VerifierClient {
    pending: VecDeque<Evidence>,
    #[cfg(feature = "http")]
    http_client: Client,
    #[cfg(feature = "http")]
    verifier_url: String,
}

impl VerifierClient {
    #[cfg(not(feature = "http"))]
    pub fn new() -> Self {
        Self { pending: VecDeque::new() }
    }

    #[cfg(feature = "http")]
    pub fn new(url: &str) -> Self {
        Self {
            pending: VecDeque::new(),
            http_client: Client::new(),
            verifier_url: url.to_string(),
        }
    }

    pub fn submit_evidence(&mut self, evidence: Evidence) {
        self.pending.push_back(evidence);
    }

    pub fn flush(&mut self) -> Vec<Evidence> {
        self.pending.drain(..).collect()
    }

    #[cfg(feature = "http")]
    pub async fn send_pending(&mut self) -> Vec<EvidenceStatus> {
        let mut statuses = Vec::new();
        while let Some(ev) = self.pending.pop_front() {
            let serialized = serde_json::to_vec(&ev).unwrap();
            let response = self.http_client.post(&self.verifier_url)
                .body(serialized)
                .header("Content-Type", "application/json")
                .send()
                .await;
            match response {
                Ok(resp) if resp.status().is_success() => statuses.push(EvidenceStatus::Accepted),
                Ok(resp) => statuses.push(EvidenceStatus::Rejected(format!("HTTP {}", resp.status()))),
                Err(e) => statuses.push(EvidenceStatus::Rejected(e.to_string())),
            }
        }
        statuses
    }

    #[cfg(not(feature = "http"))]
    pub async fn send_pending(&mut self) -> Vec<EvidenceStatus> {
        // No HTTP, just clear pending and return pending status
        self.pending.drain(..).map(|_| EvidenceStatus::Pending).collect()
    }
}
