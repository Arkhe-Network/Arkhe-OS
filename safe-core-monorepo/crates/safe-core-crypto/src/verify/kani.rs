// crates/safe-core-crypto/src/verify/kani.rs
#[kani::proof]
fn prove_did_determinism_symbolic() {
    let key_bytes: [u8; 32] = kani::any();
    if key_bytes[0] != 0 {
        let did1 = crate::did::DidArkhe::derive(&key_bytes).unwrap();
        let did2 = crate::did::DidArkhe::derive(&key_bytes).unwrap();
        assert!(did1.uri() == did2.uri());
    }
}
