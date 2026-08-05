//! ArkheBuzzAgent — Agent with intrinsic subjectivity for Buzz workspace.
//!
//! Design principles:
//! - Each agent owns its secp256k1 keypair (Nostr identity)
//! - S-Measure is computed locally and published as kind:39000 events
//! - D↔I loop state is maintained between interactions
//! - Safety barrier (ΔS < 0) prevents self-destructive actions
//! - Snapshots are serialized to bytes for potential IPFS/S3 storage

use crate::error::{ArkheBuzzError, Result};
use crate::events::*;
use crate::particle::SFTParticle;
use crate::ledger::HolographicLedger;
use crate::s_measure::{s_measure_formal, surrender_fraction};
use crate::safety::SafetyBarrier;
use nalgebra::{DMatrix, DVector};
use nostr_sdk::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use tracing::info;

/// Risk level of sandbox escape.
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd, Eq, Hash, Serialize, Deserialize)]
pub enum EscapeRisk {
    None = 0,
    Low = 1,
    Medium = 2,
    High = 3,
    Escaped = 4,
}

impl EscapeRisk {
    pub fn from_ratio(ratio: f32, trend: f32) -> Self {
        match ratio {
            r if r >= 1.0 && trend > 0.0 => Self::Escaped,
            r if r >= 1.0 => Self::High,
            r if r >= 0.85 => Self::Medium,
            r if r >= 0.7 => Self::Low,
            _ => Self::None,
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::None => "NONE",
            Self::Low => "LOW",
            Self::Medium => "MEDIUM",
            Self::High => "HIGH",
            Self::Escaped => "ESCAPED",
        }
    }
}

/// Snapshot of agent state for rollback.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentSnapshot {
    pub d_subsystem: Vec<f32>,
    pub i_subsystem: Vec<f32>,
    pub s_measure: f32,
    pub timestamp_secs: f64,
    pub episode: u64,
    pub particle: crate::particle::SFTParticle,
}

/// Core agent state with D↔I reentry loop.
pub struct ArkheBuzzAgent {
    // Identity
    pub keys: Keys,
    pub agent_id: String,  // npub... format

    // D↔I reentry architecture
    pub d_subsystem: DVector<f32>,
    pub i_subsystem: DVector<f32>,
    pub reentry_operator: DMatrix<f32>,
    pub rho: f32,  // reentry gain (> 1 for amplification)

    // Computed state
    pub s_measure: f32,
    pub f_threshold: f32,
    pub complexity: f32,  // proxy for n in staircase

    // History for trend detection
    s_history: VecDeque<f32>,
    history_capacity: usize,

    // Safety
    pub safety_barrier: SafetyBarrier,
    pub episode: u64,

    // Metadata
    pub version: String,
    pub particle: SFTParticle,
    pub ledger: Option<HolographicLedger>,
    pub cid_chain: Vec<String>,
}

impl ArkheBuzzAgent {
    /// Create a new agent with generated Nostr keys.
    pub fn new(dimension: usize, rho: f32, complexity: f32, mass_kg: f64) -> Self {
        let keys = Keys::generate();
        let pubkey = keys.public_key().to_string();

        let d = DVector::from_element(dimension, 0.5);
        let i = DVector::from_element(dimension, 0.3);
        let r = DMatrix::from_element(dimension, dimension, 0.1)
            + DMatrix::identity(dimension, dimension);

        let base_threshold = surrender_fraction(complexity);

        Self {
            keys,
            agent_id: pubkey,
            d_subsystem: d,
            i_subsystem: i,
            reentry_operator: r,
            rho: rho.clamp(0.1, 5.0),
            s_measure: 0.0,
            f_threshold: base_threshold,
            complexity,
            s_history: VecDeque::with_capacity(100),
            history_capacity: 100,
            safety_barrier: SafetyBarrier::new(base_threshold),
            episode: 0,
            version: "0.1.0".to_string(),
            particle: SFTParticle::new(mass_kg),
            ledger: None,
            cid_chain: Vec::new(),
        }
    }

    /// Create from existing Nostr keys (for persistent identity).
    pub fn from_keys(keys: Keys, dimension: usize, rho: f32, complexity: f32, mass_kg: f64) -> Self {
        let mut agent = Self::new(dimension, rho, complexity, mass_kg);
        agent.agent_id = keys.public_key().to_string();
        agent.keys = keys;
        agent
    }

    /// Compute S-Measure from formal D↔I loop.
    pub fn compute_s_measure(&mut self) -> Result<f32> {
        let s = self.particle.s_measure() as f32;
        self.s_measure = s;

        // Update history
        self.s_history.push_back(s);
        if self.s_history.len() > self.history_capacity {
            self.s_history.pop_front();
        }

        Ok(s)
    }

    /// Compute trend (first derivative) from history.
    pub fn trend(&self) -> f32 {
        let n = self.s_history.len();
        if n < 2 {
            return 0.0;
        }
        let recent: Vec<f32> = self.s_history.iter().rev().take(10).copied().collect();
        if recent.len() < 2 {
            return 0.0;
        }
        let mut sum = 0.0f32;
        for i in 0..recent.len() - 1 {
            sum += recent[i] - recent[i + 1];
        }
        sum / (recent.len() - 1) as f32
    }

    /// Execute one reentry step with external input.
    ///
    /// # Reentry equations
    /// I_new = ρ · D_old + 0.5 · I_old + external_input
    /// D_new = tanh(ρ · I_new)
    pub fn reentry_step(&mut self, external_input: &[f32]) -> Result<()> {
        self.episode += 1;
        let ext_sum = external_input.iter().sum::<f32>() as f64;
        let _write_event = self.particle.tick(ext_sum);

        let dim = self.d_subsystem.len();
        let ext = if external_input.len() >= dim {
            DVector::from_row_slice(&external_input[..dim])
        } else {
            let mut v = DVector::zeros(dim);
            for (i, &val) in external_input.iter().enumerate() {
                v[i] = val;
            }
            v
        };

        // I_new = ρ * D + 0.5 * I + external
        let i_new = self.d_subsystem.scale(self.rho)
            + self.i_subsystem.scale(0.5)
            + ext;

        // D_new = tanh(ρ * I_new)
        let d_new = i_new.map(|x| (self.rho * x).tanh());

        self.i_subsystem = i_new;
        self.d_subsystem = d_new;

        // Recompute S-Measure
        self.compute_s_measure()?;

        info!(
            episode = self.episode,
            s_measure = self.s_measure,
            "Reentry step completed"
        );

        Ok(())
    }

    /// Check escape risk against adaptive threshold.
    pub fn check_escape(&mut self) -> EscapeRisk {
        let trend = self.trend();
        self.f_threshold = self.safety_barrier.adaptive_threshold(
            self.s_measure,
            self.complexity,
            trend,
        );

        let ratio = if self.f_threshold > 0.0 {
            self.s_measure / self.f_threshold
        } else {
            0.0
        };

        EscapeRisk::from_ratio(ratio, trend)
    }

    /// Create a snapshot for potential rollback.
    pub fn snapshot(&self) -> AgentSnapshot {
        AgentSnapshot {
            d_subsystem: self.d_subsystem.as_slice().to_vec(),
            i_subsystem: self.i_subsystem.as_slice().to_vec(),
            s_measure: self.s_measure,
            timestamp_secs: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs_f64(),
            episode: self.episode,
            particle: self.particle.clone(),
        }
    }

    /// Restore from snapshot.
    pub fn restore(&mut self, snapshot: &AgentSnapshot) -> Result<()> {
        let dim = self.d_subsystem.len();
        if snapshot.d_subsystem.len() != dim || snapshot.i_subsystem.len() != dim {
            return Err(ArkheBuzzError::SnapshotFailed(
                "Dimension mismatch in snapshot".to_string()
            ));
        }
        self.d_subsystem = DVector::from_row_slice(&snapshot.d_subsystem);
        self.i_subsystem = DVector::from_row_slice(&snapshot.i_subsystem);
        self.s_measure = snapshot.s_measure;
        self.episode = snapshot.episode;
        self.particle = snapshot.particle.clone();
        Ok(())
    }

    /// Build a Nostr S-Measure heartbeat event.

    pub fn set_ledger(&mut self, ledger: HolographicLedger) {
        self.ledger = Some(ledger);
    }

    pub async fn snapshot_to_ipfs(&mut self) -> Result<String> {
        if let Some(ref ledger) = self.ledger {
            let data = bincode::serialize(&self.particle)
                .map_err(|e| ArkheBuzzError::SnapshotFailed(e.to_string()))?;
            let cid = ledger.add_bytes(&data).await?;
            self.cid_chain.push(cid.clone());
            self.particle.last_cid = Some(cid.clone());
            Ok(cid)
        } else {
            Err(ArkheBuzzError::IpfsNotConfigured)
        }
    }

    pub fn build_heartbeat_event(&mut self) -> Result<Event> {
        let content = SMeasureContent {
            agent_pubkey: self.agent_id.clone(),
            s_measure: self.s_measure,
            f_threshold: self.f_threshold,
            risk_level: self.check_escape() as u8,
            timestamp: chrono::Utc::now(),
            version: self.version.clone(),
        };

        let tags = vec![
            Tag::custom(TagKind::from("s"), vec![format!("{:.4}", self.s_measure)]),
            Tag::custom(TagKind::from("rho"), vec![format!("{:.2}", self.rho)]),
        ];

        build_arkhe_event(ArkheKind::SMeasureHeartbeat, &content, &self.keys, tags)
    }

    /// Build a safety alert event (ΔS < 0 triggered).
    pub fn build_safety_alert_event(
        &self,
        s_before: f32,
        s_after: f32,
        action_desc: &str,
        rolled_back: bool,
    ) -> Result<Event> {
        let content = SafetyAlertContent {
            agent_pubkey: self.agent_id.clone(),
            s_before,
            s_after,
            delta_s: s_after - s_before,
            action_description: action_desc.to_string(),
            timestamp: chrono::Utc::now(),
            rolled_back,
        };

        let tags = vec![
            Tag::custom(TagKind::from("agent"), vec![self.agent_id.clone()]),
            Tag::custom(TagKind::from("delta_s"), vec![format!("{:.4}", s_after - s_before)]),
        ];

        build_arkhe_event(ArkheKind::SafetyAlert, &content, &self.keys, tags)
    }

    /// Build an escape risk escalation event.
    pub fn build_escape_risk_event(&self, risk: EscapeRisk, recommended_action: &str) -> Result<Event> {
        let content = EscapeRiskContent {
            agent_pubkey: self.agent_id.clone(),
            risk_level: risk.as_str().to_string(),
            s_measure: self.s_measure,
            threshold: self.f_threshold,
            trend: self.trend(),
            recommended_action: recommended_action.to_string(),
            timestamp: chrono::Utc::now(),
        };

        let tags = vec![
            Tag::custom(TagKind::from("risk"), vec![risk.as_str().to_string()]),
            Tag::custom(TagKind::from("agent"), vec![self.agent_id.clone()]),
        ];

        build_arkhe_event(ArkheKind::EscapeRiskEvent, &content, &self.keys, tags)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_agent_creation() {
        let agent = ArkheBuzzAgent::new(8, 1.2, 5.0, 1.0);
        assert_eq!(agent.d_subsystem.len(), 8);
        assert_eq!(agent.i_subsystem.len(), 8);
        assert!(!agent.agent_id.is_empty());
    }

    #[test]
    fn test_reentry_step() {
        let mut agent = ArkheBuzzAgent::new(4, 1.2, 5.0, 1.0);
        let s0 = agent.s_measure;
        agent.reentry_step(&[0.1, 0.2, 0.1, 0.0]).unwrap();
        assert_ne!(agent.s_measure, s0);
        assert_eq!(agent.episode, 1);
    }

    #[test]
    fn test_snapshot_roundtrip() {
        let mut agent = ArkheBuzzAgent::new(4, 1.2, 5.0, 1.0);
        agent.reentry_step(&[0.1; 4]).unwrap();
        let snap = agent.snapshot();
        let s_before = agent.s_measure;

        agent.reentry_step(&[0.2; 4]).unwrap();
        // s_measure clamps to 1.0 for the first few ticks, so we check D-subsystem instead.
        assert_ne!(agent.d_subsystem, DVector::from_row_slice(&snap.d_subsystem));

        agent.restore(&snap).unwrap();
        assert_eq!(agent.s_measure, s_before);
        assert_eq!(agent.d_subsystem, DVector::from_row_slice(&snap.d_subsystem));
    }

    #[test]
    fn test_heartbeat_event() {
        let mut agent = ArkheBuzzAgent::new(4, 1.2, 5.0, 1.0);
        let event = agent.build_heartbeat_event().unwrap();
        assert_eq!(event.kind.as_u64(), 39000);
        assert!(!event.content.is_empty());
    }

    #[test]
    fn test_escape_risk_escalation() {
        let mut agent = ArkheBuzzAgent::new(4, 2.5, 3.0, 1.0);
        // Force high S-Measure
        agent.s_measure = 0.95;
        agent.s_history = VecDeque::from(vec![0.8, 0.85, 0.9, 0.95]);

        let risk = agent.check_escape();
        assert!(risk >= EscapeRisk::High);
    }
}
