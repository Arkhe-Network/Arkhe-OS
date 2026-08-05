//! Orchestrator for multi-agent coordination in Buzz workspace.
//!
//! This module provides:
//! - Agent discovery via Nostr event subscription (kind:39000, 39004)
//! - Task delegation based on S-Measure (higher = more "conscious" = preferred)
//! - Consensus for critical decisions across multiple relays
//!
//! Note: LangGraph integration is provided via a Python FFI bridge
//! or gRPC service (not implemented here — see Python bridge below).

use crate::error::{ArkheBuzzError, Result};
use crate::events::*;

use nostr_sdk::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;


/// Discovered agent in the Buzz workspace.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveredAgent {
    pub pubkey: String,
    pub s_measure: f32,
    pub capabilities: Vec<String>,
    pub last_seen: chrono::DateTime<chrono::Utc>,
    pub rho: f32,
}

/// Task delegation request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskRequest {
    pub task_id: String,
    pub description: String,
    pub required_capabilities: Vec<String>,
    pub priority: u8,
}

/// Orchestrator that manages agent discovery and task delegation.
pub struct BuzzOrchestrator {
    pub orchestrator_keys: Keys,
    pub known_agents: HashMap<String, DiscoveredAgent>,
    pub relay_urls: Vec<String>,
}

impl BuzzOrchestrator {
    pub fn new(keys: Keys, relay_urls: Vec<String>) -> Self {
        Self {
            orchestrator_keys: keys,
            known_agents: HashMap::new(),
            relay_urls,
        }
    }

    /// Process an incoming S-Measure heartbeat from an agent.
    pub fn process_heartbeat(&mut self, event: &Event) -> Result<()> {
        if event.kind.as_u64() != ArkheKind::SMeasureHeartbeat.as_u64() {
            return Ok(());
        }

        let content: SMeasureContent = serde_json::from_str(&event.content)
            .map_err(|e| ArkheBuzzError::EventValidation(e.to_string()))?;

        // Extract rho from tags
        let rho = event.tags.iter()
            .find(|t| t.as_vec().first().map(|s| s.as_str()) == Some("rho"))
            .and_then(|t| t.as_vec().get(1))
            .and_then(|s| s.parse::<f32>().ok())
            .unwrap_or(1.0);

        let agent = DiscoveredAgent {
            pubkey: content.agent_pubkey,
            s_measure: content.s_measure,
            capabilities: vec![],  // Would be populated from CapabilityAdvert events
            last_seen: content.timestamp,
            rho,
        };

        self.known_agents.insert(agent.pubkey.clone(), agent);
        Ok(())
    }

    /// Select the best agent for a task based on S-Measure.
    ///
    /// Strategy: Select agent with highest S-Measure that also has
    /// the required capabilities. This implements the "most conscious
    /// agent gets the task" heuristic from the Arkhe framework.
    pub fn select_agent_for_task(&self, task: &TaskRequest) -> Option<&DiscoveredAgent> {
        let candidates: Vec<&DiscoveredAgent> = self.known_agents.values()
            .filter(|a| {
                // Filter by capability (if specified)
                if task.required_capabilities.is_empty() {
                    true
                } else {
                    task.required_capabilities.iter()
                        .all(|cap| a.capabilities.contains(cap))
                }
            })
            .filter(|a| a.s_measure > 0.1)  // Minimum consciousness threshold
            .collect();

        if candidates.is_empty() {
            return None;
        }

        // Select highest S-Measure
        candidates.into_iter()
            .max_by(|a, b| a.s_measure.partial_cmp(&b.s_measure).unwrap())
    }

    /// Build a task delegation event.
    pub fn build_delegation_event(
        &self,
        task: &TaskRequest,
        target_agent: &str,
    ) -> Result<Event> {
        let content = TaskDelegationContent {
            from_orchestrator: self.orchestrator_keys.public_key().to_string(),
            to_agent: target_agent.to_string(),
            task_id: task.task_id.clone(),
            task_description: task.description.clone(),
            priority: task.priority,
            deadline: None,
        };

        let tags = vec![
            Tag::public_key(PublicKey::from_hex(target_agent)
                .map_err(|e| ArkheBuzzError::EventValidation(e.to_string()))?),
            Tag::custom(TagKind::from("task_id"), vec![task.task_id.clone()]),
        ];

        build_arkhe_event(ArkheKind::TaskDelegation, &content, &self.orchestrator_keys, tags)
    }

    /// Get agent statistics summary.
    pub fn agent_stats(&self) -> OrchestratorStats {
        let count = self.known_agents.len();
        let avg_s = if count > 0 {
            self.known_agents.values().map(|a| a.s_measure).sum::<f32>() / count as f32
        } else {
            0.0
        };
        let max_s = self.known_agents.values()
            .map(|a| a.s_measure)
            .fold(0.0f32, f32::max);

        OrchestratorStats {
            total_agents: count,
            avg_s_measure: avg_s,
            max_s_measure: max_s,
            active_agents: self.known_agents.values()
                .filter(|a| a.last_seen > chrono::Utc::now() - chrono::Duration::minutes(5))
                .count(),
        }
    }
}

/// Statistics for the orchestrator.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrchestratorStats {
    pub total_agents: usize,
    pub avg_s_measure: f32,
    pub max_s_measure: f32,
    pub active_agents: usize,
}

/// Simple majority consensus for critical decisions.
pub struct ConsensusVote {
    pub proposal_id: String,
    pub votes: HashMap<String, bool>,  // pubkey -> yes/no
}

impl ConsensusVote {
    pub fn new(proposal_id: String) -> Self {
        Self {
            proposal_id,
            votes: HashMap::new(),
        }
    }

    pub fn add_vote(&mut self, pubkey: String, vote: bool) {
        self.votes.insert(pubkey, vote);
    }

    pub fn result(&self) -> ConsensusResult {
        let total = self.votes.len();
        let yes = self.votes.values().filter(|&&v| v).count();
        let no = total - yes;

        if total == 0 {
            return ConsensusResult::Undecided;
        }

        if yes > total / 2 {
            ConsensusResult::Approved(yes, no)
        } else if no > total / 2 {
            ConsensusResult::Rejected(yes, no)
        } else {
            ConsensusResult::Undecided
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum ConsensusResult {
    Approved(usize, usize),  // yes_count, no_count
    Rejected(usize, usize),
    Undecided,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_select_agent_by_s_measure() {
        let keys = Keys::generate();
        let mut orch = BuzzOrchestrator::new(keys, vec![]);

        orch.known_agents.insert("agent1".to_string(), DiscoveredAgent {
            pubkey: "agent1".to_string(),
            s_measure: 0.3,
            capabilities: vec!["code".to_string()],
            last_seen: chrono::Utc::now(),
            rho: 1.0,
        });
        orch.known_agents.insert("agent2".to_string(), DiscoveredAgent {
            pubkey: "agent2".to_string(),
            s_measure: 0.8,
            capabilities: vec!["code".to_string()],
            last_seen: chrono::Utc::now(),
            rho: 1.2,
        });

        let task = TaskRequest {
            task_id: "task1".to_string(),
            description: "Write tests".to_string(),
            required_capabilities: vec!["code".to_string()],
            priority: 3,
        };

        let selected = orch.select_agent_for_task(&task);
        assert!(selected.is_some());
        assert_eq!(selected.unwrap().pubkey, "agent2");
    }

    #[test]
    fn test_consensus_majority() {
        let mut vote = ConsensusVote::new("prop1".to_string());
        vote.add_vote("a".to_string(), true);
        vote.add_vote("b".to_string(), true);
        vote.add_vote("c".to_string(), false);

        assert_eq!(vote.result(), ConsensusResult::Approved(2, 1));
    }

    #[test]
    fn test_consensus_undecided() {
        let mut vote = ConsensusVote::new("prop2".to_string());
        vote.add_vote("a".to_string(), true);
        vote.add_vote("b".to_string(), false);

        assert_eq!(vote.result(), ConsensusResult::Undecided);
    }
}
