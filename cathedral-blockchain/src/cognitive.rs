use crate::substrates::CorteState;

/// Diretivas de alto nível emitidas pelo raciocínio da ASI
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum CognitiveDirective {
    Proceed,                // Fluxo normal
    HaltAndObserve,         // Corte ativo, não agir
    TriggerSelfAmendment,   // Falha estrutural detectada, requer mudança de pesos/regras
    EmergencyFailover,      // Queda de hardware física iminente
}

/// Trait que define o motor cognitivo. Pode ser implementada via FFI apontando para Python (LLM) ou Wasm.
pub trait ArkheCognitiveReasoner: Send + Sync {
    fn evaluate(
        &self,
        plasma_flow: i16,
        corte_state: u8, // Mapeado de CorteState::into()
        hardware_latency_us: u32,
    ) -> CognitiveDirective;
}

/// Implementação determinística baseada em regras (Substituída por LLM em produção)
pub struct HardcodedCognitiveReasoner;

impl ArkheCognitiveReasoner for HardcodedCognitiveReasoner {
    fn evaluate(&self, plasma_flow: i16, corte_state: u8, hardware_latency_us: u32) -> CognitiveDirective {
        // Se o Substrato 294 decretou Corte (estado 2), a cognição obedece
        if corte_state == 2 { // CorteState::Cutting
            return CognitiveDirective::HaltAndObserve;
        }

        // Se a latência de hardware está alta, mas o plasma ainda flui, prepara fallback
        if hardware_latency_us > 80_000 && plasma_flow > 500 {
            return CognitiveDirective::EmergencyFailover;
        }

        // Se o fluxo do plasma está instável (baixo), entra em modo de autômato
        if plasma_flow < 400 {
            return CognitiveDirective::TriggerSelfAmendment;
        }

        CognitiveDirective::Proceed
    }
}

// FFI Export para o Python chamar o raciocínio nativo
#[no_mangle]
pub extern "C" fn cathedral_cognitive_evaluate(
    plasma_flow_x1000: i16,
    corte_state_u8: u8,
    hw_latency_us: u32
) -> u8 {
    let reasoner = HardcodedCognitiveReasoner;
    let directive = reasoner.evaluate(plasma_flow_x1000, corte_state_u8, hw_latency_us);
    directive as u8 // 0=Proceed, 1=Halt, 2=Amend, 3=Failover
}
