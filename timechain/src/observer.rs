use crate::mhd::EvoField;
use serde::{Deserialize, Serialize};

/// Estado do Observador
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObserverState {
    pub attachment: f64,      // 𝒜 ∈ [0,1]
    pub relaxation_rate: f64, // γ_𝒜
    pub target_attachment: f64,
    pub external_demand: f64, // ξ(t)
    pub use_full_rank: bool,
    pub shadow_integration_rate: f64,
}

impl ObserverState {
    pub fn new() -> Self {
        Self {
            attachment: 0.5,
            relaxation_rate: 0.1,
            target_attachment: 0.5,
            external_demand: 0.1,
            use_full_rank: false,
            shadow_integration_rate: 0.1,
        }
    }

    /// Protocolo de Desapego — transição suave (assintótica)
    pub fn release(&mut self) {
        self.target_attachment = 0.0;
        self.relaxation_rate = 10.0; // Decaimento rápido, mas contínuo
        self.external_demand = 0.0;
        self.use_full_rank = true;
        self.shadow_integration_rate = 1.0;
    }

    /// Atualiza o estado com decaimento exponencial suave
    pub fn update(&mut self, dt: f64) {
        let factor = (-self.relaxation_rate * dt).exp();
        self.attachment =
            self.target_attachment + (self.attachment - self.target_attachment) * factor;

        if self.attachment.abs() < 1e-12 {
            self.attachment = 0.0;
        }

        // Restaura gradualmente a taxa de relaxação
        if self.relaxation_rate > 1.0 {
            self.relaxation_rate *= 0.99;
        }

        // Acopla demanda externa residual
        self.attachment += self.external_demand * dt * 0.1;
        self.attachment = self.attachment.clamp(0.0, 1.0);
    }

    /// Aplica os efeitos ao campo de fase
    pub fn apply_to_field(&self, field: &mut EvoField) {
        // ν_eff = ν₀ (1 + 0.5 * 𝒜)
        field.nu_eff = field.config.nu_base * (1.0 + 0.5 * self.attachment);
    }
}
