use crate::{
    aotb::AotbEncoderHw, power::PowerDomain, qpl::QplAccelerator, sram::SramDxController,
    AotbFrame, ClockDomain, PerformanceCounters, QplResult, DOMAIN_NODES,
};

pub struct ArkheSoc {
    pub sram: SramDxController,
    pub qpl: QplAccelerator,
    pub power: PowerDomain,
    pub session_id: [u8; 16],
    pub proof_hash: [u8; 32],
    pub weights: [u8; DOMAIN_NODES],
    clock: ClockDomain,
}

impl ArkheSoc {
    pub fn new(domain: [f64; DOMAIN_NODES], session_id: [u8; 16], clock: ClockDomain) -> Self {
        let proof_hash = crate::hash_state(&domain);
        let mut sram = SramDxController::new(ClockDomain::new(clock.freq_mhz));
        for (i, &v) in domain.iter().enumerate() {
            sram.write_domain_d(i as u8, v).unwrap();
        }
        sram.expand_and_swap(0, &[100; DOMAIN_NODES]);

        Self {
            sram,
            qpl: QplAccelerator::new(ClockDomain::new(clock.freq_mhz)),
            power: PowerDomain::new("PD_CORE", clock.freq_mhz),
            session_id,
            proof_hash,
            weights: [100; DOMAIN_NODES],
            clock,
        }
    }

    pub fn qpl_forward(&mut self) -> Result<[QplResult; DOMAIN_NODES], crate::SocError> {
        self.qpl.config.control = 1; // start
        self.qpl.config.iterations = 1;
        self.qpl.execute_convolution(&self.sram)
    }

    pub fn expand(&mut self, sequence: u64) -> u64 {
        let cycles = self.sram.expand_and_swap(sequence, &self.weights);
        self.clock.tick(cycles);
        cycles
    }

    pub fn emit_frame(
        &mut self,
        encoder: &mut AotbEncoderHw,
    ) -> Result<AotbFrame, crate::SocError> {
        let mut values = [0.0; DOMAIN_NODES];
        for i in 0..DOMAIN_NODES {
            values[i] = self.sram.read_domain_d(i as u8).unwrap_or(0.0);
        }
        encoder.next_frame(values, self.weights)
    }

    pub fn counters(&self) -> PerformanceCounters {
        let mut c = PerformanceCounters::default();
        c.qpl_cycles = self.qpl.counters.qpl_cycles;
        c.expand_cycles = self.qpl.counters.expand_cycles;
        c.power_mw = self.power.estimate_power_mw();
        c
    }
}
