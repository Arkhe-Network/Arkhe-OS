use crate::{AotbFrame, ClockDomain, DOMAIN_NODES, PerformanceCounters, SocError, VerifyError};
use ed25519_dalek::{Signer, SigningKey, Verifier, VerifyingKey};

pub struct AotbEncoderHw {
    signing_key: SigningKey,
    session_id: [u8; 16],
    next_sequence: u64,
    proof_hash: [u8; 32],
    clock: ClockDomain,
    counters: PerformanceCounters,
}

impl AotbEncoderHw {
    pub fn new(
        signing_key: SigningKey,
        session_id: [u8; 16],
        proof_hash: [u8; 32],
        clock: ClockDomain,
    ) -> Self {
        Self {
            signing_key,
            session_id,
            next_sequence: 0,
            proof_hash,
            clock,
            counters: PerformanceCounters::default(),
        }
    }

    pub fn next_frame(
        &mut self,
        domain_values: [f64; DOMAIN_NODES],
        weights: [u8; DOMAIN_NODES],
    ) -> Result<AotbFrame, SocError> {
        let start_cycles = self.clock.total_cycles();
        let sequence = self.next_sequence;
        self.next_sequence += 1;
        let nonce = sequence;

        let frame = AotbFrame {
            session_id: self.session_id,
            sequence,
            nonce,
            proof_hash: self.proof_hash,
            domain_values,
            weights,
            signature: [0u8; 64], // preenchido abaixo
        };

        let payload = frame.signing_bytes();
        let sig = self.signing_key.sign(&payload);
        let mut frame = frame;
        frame.signature = sig.to_bytes();

        self.counters.encode_cycles += self.clock.total_cycles() - start_cycles;
        self.counters.frames_emitted += 1;
        Ok(frame)
    }

    pub fn counters(&self) -> &PerformanceCounters {
        &self.counters
    }
}

pub struct AotbVerifierHw {
    key: VerifyingKey,
    session_id: [u8; 16],
    next_sequence: u64,
    counters: PerformanceCounters,
}

impl AotbVerifierHw {
    pub fn new(key: VerifyingKey, session_id: [u8; 16]) -> Self {
        Self {
            key,
            session_id,
            next_sequence: 0,
            counters: PerformanceCounters::default(),
        }
    }

    pub fn verify(&mut self, frame: &AotbFrame) -> Result<(), VerifyError> {
        if frame.nonce == crate::SENTINEL {
            self.counters.frames_rejected += 1;
            return Err(VerifyError::Sentinel);
        }
        if frame.session_id != self.session_id {
            self.counters.frames_rejected += 1;
            return Err(VerifyError::SessionMismatch);
        }
        if frame.sequence != self.next_sequence || frame.nonce != frame.sequence {
            self.counters.frames_rejected += 1;
            return Err(VerifyError::SequenceMismatch);
        }

        let signature = ed25519_dalek::Signature::from_slice(&frame.signature)
            .map_err(|_| VerifyError::BadSignature)?;

        self.key
            .verify(&frame.signing_bytes(), &signature)
            .map_err(|_| VerifyError::BadSignature)?;

        self.next_sequence += 1;
        Ok(())
    }

    pub fn counters(&self) -> &PerformanceCounters {
        &self.counters
    }
}
