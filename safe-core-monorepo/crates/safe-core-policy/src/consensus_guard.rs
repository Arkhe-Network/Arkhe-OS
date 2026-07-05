// crates/safe-core-policy/src/consensus_guard.rs
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StructuralProposal {
    pub tool_name: String,
    pub inputs: Value,
    // ⚠️ SEM campo reasoning, SEM campo cot
}

pub fn evaluate_structural_confidence(
    proposal: &StructuralProposal,
    capability: &CapabilityMetadata,
    schema_provider: &dyn ToolSchemaProvider,
) -> Result<f32, ConsensusGuardError> {
    // ✅ NENHUMA análise de linguagem natural
    // ✅ NENHUMA chamada a LLM
    // ✅ Apenas verificações estruturais
    
    if !schema_provider.is_registered(&proposal.tool_name) {
        return Err(ConsensusGuardError::ToolNotRegistered(...));
    }
    
    schema_provider.validate_inputs(&proposal.tool_name, &proposal.inputs)?;
    
    let required_scope = format!("tool:{}", proposal.tool_name);
    if !capability.scope.contains(&required_scope) {
        return Err(ConsensusGuardError::InsufficientCapability { ... });
    }
    
    Ok(1.0) // Confiança máxima baseada em verificação estrutural
}
