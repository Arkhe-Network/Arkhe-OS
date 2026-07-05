use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum GuardError {
    #[error("Tool não registrado: {0}")]
    NotRegistered(String),
    #[error("Schema inválido: {0}")]
    SchemaInvalid(String),
    #[error("Sem permissão")]
    Forbidden,
}

/// INVARIANTE I13: Sem campos de texto livre. O "teatro do raciocínio" morre aqui.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Proposal {
    pub tool: String,
    pub payload: Value,
}

pub struct Policy {
    pub allowed_tools: Vec<String>,
}

impl Policy {
    pub fn evaluate(&self, proposal: &Proposal) -> Result<(), GuardError> {
        if !self.allowed_tools.contains(&proposal.tool) {
            return Err(GuardError::NotRegistered(proposal.tool.clone()));
        }

        if !proposal.payload.is_object() {
            return Err(GuardError::SchemaInvalid("Payload deve ser objeto".into()));
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_allows_valid_tool() {
        let policy = Policy { allowed_tools: vec!["read".into()] };
        let proposal = Proposal { tool: "read".into(), payload: serde_json::json!({}) };
        assert!(policy.evaluate(&proposal).is_ok());
    }

    #[test]
    fn test_blocks_unregistered_tool() {
        let policy = Policy { allowed_tools: vec!["read".into()] };
        let proposal = Proposal {
            tool: "delete".into(),
            payload: serde_json::json!({"reason": "very good reason"}),
        };
        // O "reason" é ignorado. A estrutura falha.
        assert!(matches!(policy.evaluate(&proposal), Err(GuardError::NotRegistered(_))));
    }
}
