use crate::ClockDomain;

/// Domínio de energia inspirado no MycoFi (fertility-based allocation)
pub struct PowerDomain {
    pub name: &'static str,
    pub enabled: bool,
    pub voltage_mv: u32,      // 800-1200mV
    pub freq_mhz: u32,
    pub fertility: f64,       // 0.0-1.0 (capital alocado / total)
    pub clock: ClockDomain,
}

impl PowerDomain {
    pub fn new(name: &'static str, base_freq_mhz: u32) -> Self {
        Self {
            name,
            enabled: true,
            voltage_mv: 1000,
            freq_mhz: base_freq_mhz,
            fertility: 1.0,
            clock: ClockDomain::new(base_freq_mhz),
        }
    }

    /// DVFS: ajusta frequência baseado na fertilidade (MycoFi mapping)
    pub fn update_dvfs(&mut self, total_capital: f64) {
        if total_capital <= 0.0 {
            self.enabled = false;
            self.freq_mhz = 0;
            return;
        }
        self.fertility = (self.fertility / total_capital).min(1.0);
        // Turbo se fertility > 0.8
        self.freq_mhz = if self.fertility > 0.8 {
            (self.clock.freq_mhz as f64 * 1.2) as u32
        } else if self.fertility > 0.3 {
            self.clock.freq_mhz
        } else {
            (self.clock.freq_mhz as f64 * 0.5) as u32
        };
        self.enabled = self.freq_mhz > 0;
    }

    pub fn estimate_power_mw(&self) -> u32 {
        if !self.enabled {
            return 0;
        }
        // Modelo simplificado: P ∝ V² × f
        let v = self.voltage_mv as f64 / 1000.0;
        let base = 100.0; // mW @ 1V, 100MHz
        (base * v * v * (self.freq_mhz as f64 / 100.0)) as u32
    }
}
