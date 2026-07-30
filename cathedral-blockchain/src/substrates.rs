//! Substrato 294 — Protocolo de Corte (Coupure Ontológica)
//! Implementação determinística em Rust no_std.

use core::time::Duration;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Default)]
#[repr(u8)]
pub enum CorteState {
    #[default]
    Normal = 0,
    Warning = 1,
    Cutting = 2,
    Recovering = 3,
}

#[derive(Clone, Copy, Debug)]
pub struct CorteThresholds {
    pub latency_cutoff_us: u32,      // Ex: 100_000 (100ms)
    pub loss_cutoff_ppm: u32,        // Ex: 50_000 (5%)
    pub warning_multiplier_x1000: u16, // Ex: 700 (70%)
    pub recovery_hysteresis_us: u32, // Ex: 20_000 (20ms abaixo do corte)
    pub min_cut_duration_us: u64,    // Ex: 500_000 (500ms mínimo congelado)
}

impl Default for CorteThresholds {
    fn default() -> Self {
        Self {
            latency_cutoff_us: 100_000,
            loss_cutoff_ppm: 50_000,
            warning_multiplier_x1000: 700,
            recovery_hysteresis_us: 20_000,
            min_cut_duration_us: 500_000,
        }
    }
}

/// Modificadores de estado para o PlasmaTorus.
/// Usa inteiros sinalizados. 1000 = 1.0 (normal), -1000 = -1.0 (inverso).
#[derive(Clone, Copy, Debug, Default)]
pub struct CorteAction {
    pub state: CorteState,
    pub flow_modifier_x1000: i16,     // Multiplicador de fluxo toroidal
    pub density_modifier_x1000: i16,  // Multiplicador de rigidez
    pub temp_modifier_x1000: i16,     // Modificador de temperatura
    pub force_hesitate: bool,         // Sinaliza parada lacaniana imediata
}

pub struct ProtocoloCorte294 {
    state: CorteState,
    thresholds: CorteThresholds,
    cut_triggered_tick_us: u64,
    cuts_executed_total: u32,
}

impl ProtocoloCorte294 {
    pub fn new(thresholds: CorteThresholds) -> Self {
        Self {
            state: CorteState::Normal,
            thresholds,
            cut_triggered_tick_us: 0,
            cuts_executed_total: 0,
        }
    }

    /// Avalia as métricas físicas e retorna a ação de corte.
    /// `now_us` deve ser o relógio monotônico do sistema.
    pub fn evaluate(
        &mut self,
        now_us: u64,
        latency_us: u32,
        loss_ppm: u32,
        current_flow_x1000: u16,
    ) -> CorteAction {
        let is_critical = latency_us >= self.thresholds.latency_cutoff_us
            || loss_ppm >= self.thresholds.loss_cutoff_ppm;

        let warn_lat = (self.thresholds.latency_cutoff_us as u64 * self.thresholds.warning_multiplier_x1000 as u64) / 1000;
        let warn_loss = (self.thresholds.loss_cutoff_ppm as u64 * self.thresholds.warning_multiplier_x1000 as u64) / 1000;

        let is_warning = latency_us >= warn_lat as u32 || loss_ppm >= warn_loss as u32;

        match self.state {
            CorteState::Normal => {
                if is_critical {
                    return self.execute_cut(now_us, "Limiar crítico ultrapassado");
                }
                if is_warning {
                    self.state = CorteState::Warning;
                    return CorteAction { state: CorteState::Warning, flow_modifier_x1000: 800, density_modifier_x1000: 1100, temp_modifier_x1000: 100, force_hesitate: false };
                }
                CorteAction::normal()
            }
            CorteState::Warning => {
                if is_critical { return self.execute_cut(now_us, "Falha durante aviso"); }
                if !is_warning { self.state = CorteState::Normal; return CorteAction::normal(); }
                CorteAction { state: CorteState::Warning, flow_modifier_x1000: 800, density_modifier_x1000: 1100, temp_modifier_x1000: 100, force_hesitate: false }
            }
            CorteState::Cutting => {
                let time_in_cut = now_us.saturating_sub(self.cut_triggered_tick_us);
                let recovered_lat = self.thresholds.latency_cutoff_us.saturating_sub(self.thresholds.recovery_hysteresis_us);

                if latency_us <= recovered_lat && loss_ppm <= (self.thresholds.loss_cutoff_ppm / 2) && time_in_cut > self.thresholds.min_cut_duration_us {
                    self.state = CorteState::Recovering;
                    return CorteAction { state: CorteState::Recovering, flow_modifier_x1000: 300, density_modifier_x1000: 800, temp_modifier_x1000: -100, force_hesitate: true };
                }
                // Mantém corte rígido
                CorteAction { state: CorteState::Cutting, flow_modifier_x1000: 0, density_modifier_x1000: 1500, temp_modifier_x1000: -300, force_hesitate: true }
            }
            CorteState::Recovering => {
                if is_critical || is_warning { return self.execute_cut(now_us, "Recaída na recuperação"); }
                if current_flow_x1000 < 950 {
                    let new_flow = core::cmp::min(1000, current_flow_x1000 as i16 + 200);
                    return CorteAction { state: CorteState::Recovering, flow_modifier_x1000: new_flow, density_modifier_x1000: 1000, temp_modifier_x1000: 0, force_hesitate: false };
                }
                self.state = CorteState::Normal;
                CorteAction::normal()
            }
        }
    }

    fn execute_cut(&mut self, now_us: u64, _reason: &str) -> CorteAction {
        self.state = CorteState::Cutting;
        self.cut_triggered_tick_us = now_us;
        self.cuts_executed_total += 1;
        CorteAction { state: CorteState::Cutting, flow_modifier_x1000: 0, density_modifier_x1000: 1500, temp_modifier_x1000: -300, force_hesitate: true }
    }
}

impl CorteAction {
    pub fn normal() -> Self {
        Self { state: CorteState::Normal, flow_modifier_x1000: 1000, density_modifier_x1000: 1000, temp_modifier_x1000: 0, force_hesitate: false }
    }
}
