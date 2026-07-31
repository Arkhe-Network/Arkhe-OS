use crate::{
    ArkhePeripheral, BufferId, ClockDomain, DOMAIN_NODES, FULL_NODES, SocError,
};
use std::sync::atomic::{AtomicU64, Ordering};

/// SRAM dual-port com double buffering (arXiv:2607.16100)
pub struct SramDxController {
    bank_d: [[u8; 8]; DOMAIN_NODES], // 8 vértices × 64-bit cada (f64)
    bank_x: [[u8; 8]; FULL_NODES],  // 16 vértices expandidos
    active: BufferId,
    ready_sequence: AtomicU64,
    clock: ClockDomain,
}

impl SramDxController {
    pub fn new(clock: ClockDomain) -> Self {
        Self {
            bank_d: [[0u8; 8]; DOMAIN_NODES],
            bank_x: [[0u8; 8]; FULL_NODES],
            active: BufferId::Domain,
            ready_sequence: AtomicU64::new(0),
            clock,
        }
    }

    pub fn write_domain_d(&mut self, vertex_idx: u8, value: f64) -> Result<(), SocError> {
        if vertex_idx as usize >= DOMAIN_NODES {
            return Err(SocError::InvalidAddress(vertex_idx as u32));
        }
        self.bank_d[vertex_idx as usize] = value.to_be_bytes();
        Ok(())
    }

    pub fn read_domain_d(&self, vertex_idx: u8) -> Result<f64, SocError> {
        if vertex_idx as usize >= DOMAIN_NODES {
            return Err(SocError::InvalidAddress(vertex_idx as u32));
        }
        let bytes = self.bank_d[vertex_idx as usize];
        Ok(f64::from_be_bytes(bytes))
    }

    pub fn read_ambient_x(&self, vertex_idx: u8) -> Result<f64, SocError> {
        if vertex_idx as usize >= FULL_NODES {
            return Err(SocError::InvalidAddress(vertex_idx as u32));
        }
        let bytes = self.bank_x[vertex_idx as usize];
        Ok(f64::from_be_bytes(bytes))
    }

    /// Expansão IFS (Sierpinski-4D) + swap atômico
    pub fn expand_and_swap(&mut self, sequence: u64, weights: &[u8; DOMAIN_NODES]) -> u64 {
        self.ready_sequence.store(u64::MAX, Ordering::SeqCst); // sentinel: busy

        // 1 ciclo por vértice no TLM (no RTL seria combinational)
        let mut cycles = 0u64;

        for i in 0..DOMAIN_NODES {
            let base = f64::from_be_bytes(self.bank_d[i]);
            let neighbor = f64::from_be_bytes(self.bank_d[(i + 1) % DOMAIN_NODES]);
            let weight = f64::from(weights[i]) / 100.0;
            let expanded = weight * base + (1.0 - weight) * neighbor;

            self.bank_x[i] = self.bank_d[i]; // inclusão direta (bandIso toFun)
            self.bank_x[i + DOMAIN_NODES] = expanded.to_be_bytes();
            cycles += 1;
        }

        self.active = match self.active {
            BufferId::Domain => BufferId::Full,
            BufferId::Full => BufferId::Domain,
        };
        self.ready_sequence.store(sequence, Ordering::SeqCst);
        cycles
    }

    pub fn active_buffer(&self) -> BufferId {
        self.active
    }

    pub fn is_ready(&self, sequence: u64) -> bool {
        self.ready_sequence.load(Ordering::SeqCst) == sequence
    }
}

impl ArkhePeripheral for SramDxController {
    fn read_reg(&mut self, addr: u32) -> Result<u32, SocError> {
        match addr {
            0x00 => Ok(self.active_buffer() as u32),
            0x04 => Ok(self.ready_sequence.load(Ordering::SeqCst) as u32),
            0x08 => Ok((self.ready_sequence.load(Ordering::SeqCst) >> 32) as u32),
            _ => Err(SocError::InvalidAddress(addr)),
        }
    }

    fn write_reg(&mut self, addr: u32, _val: u32) -> Result<(), SocError> {
        match addr {
            0x10 => {
                // Trigger swap manual (debug)
                self.expand_and_swap(0, &[100; DOMAIN_NODES]);
                Ok(())
            }
            _ => Err(SocError::InvalidAddress(addr)),
        }
    }
}
