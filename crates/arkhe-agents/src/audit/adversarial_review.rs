// crates/arkhe-agents/src/audit/adversarial_review.rs
//! Agente de revisão adversária — tenta refutar cada PR antes do merge.

use arkhe_llm::engine::InferenceEngine;
use arkhe_metacognition::Escalator;
use std::sync::Arc;
use arkhe_core::ArkheError;

pub enum ReviewVerdict {
    Verified,
    Rejected(String),
}

pub struct AdversarialReviewer {
    llm: Arc<dyn InferenceEngine>,
    escalator: Escalator,
}

impl AdversarialReviewer {
    pub async fn review_pr(
        &self,
        pr_description: &str,
        diff: &str,
    ) -> Result<ReviewVerdict, ArkheError> {
        let prompt = format!(
            r#"
            You are an adversarial reviewer. Your job is to DISPROVE the safety of this PR.

            PR: {}
            Diff:
            {}

            Find at least one concrete attack scenario that exploits this change.
            If you cannot find one, state 'VERIFIED: safe'.
            If you find one, state 'REJECTED: [attack scenario]'.
            "#,
            pr_description, diff
        );

        let response = self.llm.generate(&prompt, 0.3, 4096).await.map_err(|e| ArkheError::Internal(e))?;

        if response.contains("REJECTED") {
            self.escalator.escalate(pr_description, &response).await;
            Ok(ReviewVerdict::Rejected(response))
        } else {
            Ok(ReviewVerdict::Verified)
        }
    }
}
