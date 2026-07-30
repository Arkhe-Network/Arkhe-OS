//! Arkhe Security Audit — Pipeline de 6 fases da Cloudflare
//!
//! 1. Reconnaissance — Mapeia arquitetura e superfícies de ataque
//! 2. Hunt — Agentes paralelos caçam vulnerabilidades
//! 3. Validate — Agentes tentam refutar cada achado
//! 4. Report — Gera relatórios humanos e detalhados
//! 5. Structured Output — findings.json validado por schema
//! 6. Independent Verification — Agentes frescos verificam cada alegação

pub mod recon;
pub mod hunt;
pub mod validate;
pub mod report;
pub mod structured_output;
pub mod independent_verification;

pub mod types;

pub use types::{Finding, Severity, AttackClass};
pub use recon::ReconnaissancePhase;
pub use hunt::HuntPhase;
pub use validate::ValidationPhase;
pub use report::ReportPhase;
pub use structured_output::StructuredOutputPhase;
pub use independent_verification::IndependentVerificationPhase;

/// Orquestrador que executa as 6 fases em sequência.
pub struct AuditOrchestrator {
    target_dir: String,
    llm: std::sync::Arc<dyn arkhe_llm::engine::InferenceEngine>,
}

impl AuditOrchestrator {
    pub fn new(target_dir: &str, llm: std::sync::Arc<dyn arkhe_llm::engine::InferenceEngine>) -> Self {
        Self {
            target_dir: target_dir.to_string(),
            llm,
        }
    }

    pub async fn run(&self) -> Result<Vec<Finding>, arkhe_core::ArkheError> {
        tracing::info!("🔄 Iniciando auditoria de segurança (6 fases)");

        // Fase 1: Reconhecimento
        let recon = ReconnaissancePhase::new(&self.target_dir, self.llm.clone());
        let architecture = recon.run().await?;

        // Fase 2: Caça
        let hunt = HuntPhase::new(self.llm.clone());
        let findings = hunt.run(&architecture).await?;

        // Fase 3: Validação (adversarial)
        let validate = ValidationPhase::new(self.llm.clone());
        let validated_findings = validate.run(findings).await?;

        // Fase 4: Relatório
        let report = ReportPhase::new();
        report.generate(&validated_findings).await?;

        // Fase 5: Saída Estruturada
        let structured = StructuredOutputPhase::new();
        structured.generate(&validated_findings).await?;

        // Fase 6: Verificação Independente
        let verify = IndependentVerificationPhase::new(self.llm.clone());
        let verified_findings = verify.run(validated_findings).await?;

        Ok(verified_findings)
    }
}
