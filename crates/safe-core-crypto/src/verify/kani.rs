//! Prova Kani: prefixo e determinismo da derivação de DID.

#[kani::proof]
fn prove_did_prefix_is_correct() {
    let key_bytes: [u8; 32] = kani::any();

    // Invariante de domínio: chave não pode ser toda-zero (senão o unwrap falha
    // apenas se estiver vazia, mas mantemos a checagem simbólica robusta).
    let is_empty = key_bytes.iter().all(|&b| b == 0);

    if !is_empty {
        let did = crate::did::DidArkhe::derive(&key_bytes).unwrap();
        let uri = did.uri();

        assert!(uri.starts_with("did:arkhe:"));

        // CORREÇÃO: "did:arkhe:" tem 10 caracteres. O slice começa no índice 10.
        let hash_part = &uri[10..];
        assert_eq!(hash_part.len(), 64);
    }
}

#[kani::proof]
fn prove_did_determinism_symbolic() {
    let key_bytes: [u8; 32] = kani::any();

    let is_empty = key_bytes.iter().all(|&b| b == 0);

    if !is_empty {
        let did1 = crate::did::DidArkhe::derive(&key_bytes).unwrap();
        let did2 = crate::did::DidArkhe::derive(&key_bytes).unwrap();
        assert!(did1.uri() == did2.uri());
    }
}
