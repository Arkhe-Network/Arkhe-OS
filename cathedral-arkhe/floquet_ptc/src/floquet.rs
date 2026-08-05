//! Teoria de Floquet para a modulação periódica da massa efetiva.
//! A modulação é descrita por η(τ) = -η₀ * cos²(ω_d * τ)

#[derive(Debug, Clone)]
pub struct FloquetHamiltonian {
    pub omega_0: f64, // Frequência natural da cavidade (rad/THz)
    pub omega_d: f64, // Frequência de drive (rad/THz)
    pub eta_0: f64,   // Amplitude da modulação de massa (até 0.8)
    pub gamma_0: f64, // Amortecimento intrínseco
}

impl FloquetHamiltonian {
    /// Calcula a modulação da massa efetiva em um dado tempo τ.
    pub fn effective_mass_modulation(&self, tau: f64) -> f64 {
        -self.eta_0 * (self.omega_d * tau).cos().powi(2)
    }

    /// Calcula os autovalores de Floquet (aproximação de 2x2).
    /// μ̃_± = ω̃_d ± i(Γ₀ ± ΔΓ)
    pub fn calculate_floquet_eigenvalues(&self, tau: f64) -> (f64, f64) {
        let eta = self.effective_mass_modulation(tau);

        // A abertura do gap (simplificação do paper para regime de acoplamento forte)
        let delta_gamma = (eta.abs() - 0.1).max(0.0).sqrt();

        // Partes imaginárias dos polos
        let imag_part_pos = self.gamma_0 + delta_gamma; // Modo de ganho
        let imag_part_neg = self.gamma_0 - delta_gamma; // Modo super-amortecido

        (imag_part_pos, imag_part_neg)
    }
}
