use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EchoSignal {
    pub timestamp: f64,
    pub strength: f64,
    pub predicted_helicity: f64,
    pub origin_height: u64,
    pub pattern: Vec<f64>, // Cauda da SVD comprimida
}

impl EchoSignal {
    pub fn new(strength: f64, predicted_helicity: f64, origin: u64, pattern: Vec<f64>) -> Self {
        Self {
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs_f64(),
            strength,
            predicted_helicity,
            origin_height: origin,
            pattern,
        }
    }
}

/// Canal Retrocausal — buffer de ecos com atraso de fase
pub struct RetroCausalChannel {
    pub buffer: Vec<EchoSignal>,
    pub max_delay: f64, // Tempo de fase máximo de viagem
    pub v_eco: f64,     // Velocidade de Alfvén (base)
}

impl RetroCausalChannel {
    pub fn new(max_delay: f64, v_eco: f64) -> Self {
        Self {
            buffer: Vec::new(),
            max_delay,
            v_eco,
        }
    }

    /// Emite um eco para o canal
    pub fn emit(&mut self, echo: EchoSignal) {
        self.buffer.push(echo);
    }

    /// Recebe ecos que chegaram no tempo presente
    pub fn receive(&mut self, current_time: f64) -> Vec<EchoSignal> {
        let mut arrived = Vec::new();
        self.buffer.retain(|echo| {
            let travel_time = current_time - echo.timestamp;
            if travel_time >= 0.0 && travel_time <= self.max_delay {
                // O eco viajou e chegou
                arrived.push(echo.clone());
                false // Remove do buffer
            } else {
                true // Mantém no buffer (ainda viajando ou já passou)
            }
        });
        arrived
    }
}
