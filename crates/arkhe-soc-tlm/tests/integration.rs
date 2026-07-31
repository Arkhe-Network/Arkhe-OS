use arkhe_soc_tlm::{
    aotb::{AotbEncoderHw, AotbVerifierHw}, soc::ArkheSoc, ClockDomain, DOMAIN_NODES, VerifyError,
};
use ed25519_dalek::SigningKey;

#[test]
fn end_to_end_qpl_aotb_cycle() {
    let clock = ClockDomain::new(400);
    let key = SigningKey::from_bytes(&[3u8; 32]);
    let mut soc = ArkheSoc::new([1.0; DOMAIN_NODES], [1u8; 16], clock);
    let mut encoder = AotbEncoderHw::new(key.clone(), [1u8; 16], soc.proof_hash, ClockDomain::new(400));
    let mut verifier = AotbVerifierHw::new(key.verifying_key(), [1u8; 16]);

    for seq in 0..100u64 {
        let qpl = soc.qpl_forward().unwrap();
        assert_eq!(qpl.len(), DOMAIN_NODES);
        soc.expand(seq);
        let frame = soc.emit_frame(&mut encoder).unwrap();
        assert!(verifier.verify(&frame).is_ok());
    }
}

#[test]
fn replay_attack_detected() {
    let key = SigningKey::from_bytes(&[5u8; 32]);
    let mut encoder = AotbEncoderHw::new(key.clone(), [2u8; 16], [0u8; 32], ClockDomain::new(400));
    let mut verifier = AotbVerifierHw::new(key.verifying_key(), [2u8; 16]);
    let frame = encoder.next_frame([0.0; DOMAIN_NODES], [100; DOMAIN_NODES]).unwrap();
    assert!(verifier.verify(&frame).is_ok());
    assert_eq!(verifier.verify(&frame), Err(VerifyError::SequenceMismatch));
}
