use crate::error::{AuthError, AuthResult};
use crate::types::{FastAead, PqKem, PqSignature};
use alloc::vec::Vec;
use rand_core::CryptoRngCore;

use aes_gcm_siv::{
    aead::{generic_array::GenericArray, AeadInPlace, KeyInit}, Nonce, Tag,
};

pub struct Aes256GcmSivAead;

impl FastAead for Aes256GcmSivAead {
    fn seal(&self, key: &[u8; 32], nonce: &[u8; 12], aad: &[u8], plaintext: &mut [u8]) -> [u8; 16] {
        let key = GenericArray::from_slice(key);
        let cipher = aes_gcm_siv::Aes256GcmSiv::new(key);
        let nonce = Nonce::from_slice(nonce);

        let tag = cipher
            .encrypt_in_place_detached(nonce, aad, plaintext)
            .expect("AES-GCM-SIV encryption failure — check key/nonce validity");

        let mut tag_bytes = [0u8; 16];
        tag_bytes.copy_from_slice(tag.as_slice());
        tag_bytes
    }

    fn open(
        &self,
        key: &[u8; 32],
        nonce: &[u8; 12],
        aad: &[u8],
        ciphertext: &mut [u8],
        tag: &[u8; 16],
    ) -> AuthResult<()> {
        let key = GenericArray::from_slice(key);
        let cipher = aes_gcm_siv::Aes256GcmSiv::new(key);
        let nonce = Nonce::from_slice(nonce);
        let tag = Tag::from_slice(tag);

        cipher
            .decrypt_in_place_detached(nonce, aad, ciphertext, tag)
            .map_err(|_| AuthError::FastPathVerification)
    }
}

use pqcrypto_dilithium::dilithium3 as dilithium;
use pqcrypto_traits::sign::{
    DetachedSignature, PublicKey as PqPublicKey, SecretKey as PqSecretKey,
};

pub struct MlDsa65;

impl PqSignature for MlDsa65 {
    const PUBLIC_KEY_LEN: usize = dilithium::public_key_bytes();
    const SIGNATURE_LEN: usize = dilithium::signature_bytes();

    fn sign(&self, msg: &[u8], sk: &[u8]) -> Vec<u8> {
        let sk = dilithium::SecretKey::from_bytes(sk).expect("invalid ML-DSA secret key length");
        let sig = dilithium::detached_sign(msg, &sk);
        sig.as_bytes().to_vec()
    }

    fn verify(&self, msg: &[u8], sig: &[u8], pk: &[u8]) -> bool {
        let pk = match dilithium::PublicKey::from_bytes(pk) {
            Ok(pk) => pk,
            Err(_) => return false,
        };
        let sig = match dilithium::DetachedSignature::from_bytes(sig) {
            Ok(sig) => sig,
            Err(_) => return false,
        };
        dilithium::verify_detached_signature(&sig, msg, &pk).is_ok()
    }
}

use pqcrypto_kyber::kyber768;
use pqcrypto_traits::kem::{
    Ciphertext as KemCiphertext, PublicKey as KemPublicKey, SecretKey as KemSecretKey,
    SharedSecret as KemSharedSecret,
};
use x25519_dalek::{PublicKey as X25519PublicKey, StaticSecret as X25519StaticSecret};

pub struct XWingKem;

const KYBER_PK_LEN: usize = 1184;
const KYBER_SK_LEN: usize = 2400;
const KYBER_CT_LEN: usize = 1088;

const X25519_PK_LEN: usize = 32;
const X25519_SK_LEN: usize = 32;

impl PqKem for XWingKem {
    const CT_LEN: usize = KYBER_CT_LEN + X25519_PK_LEN; // 1120 bytes

    fn keygen(&self, rng: &mut dyn CryptoRngCore) -> (Vec<u8>, Vec<u8>) {
        let (kyber_pk, kyber_sk) = kyber768::keypair();

        let x25519_sk = X25519StaticSecret::random_from_rng(rng);
        let x25519_pk = X25519PublicKey::from(&x25519_sk);

        let mut pk = Vec::with_capacity(KYBER_PK_LEN + X25519_PK_LEN);
        pk.extend_from_slice(kyber_pk.as_bytes());
        pk.extend_from_slice(x25519_pk.as_bytes());

        let mut sk = Vec::with_capacity(KYBER_SK_LEN + X25519_SK_LEN);
        sk.extend_from_slice(kyber_sk.as_bytes());
        sk.extend_from_slice(&x25519_sk.to_bytes());

        (pk, sk)
    }

    fn encapsulate(&self, pk: &[u8], rng: &mut dyn CryptoRngCore) -> (Vec<u8>, [u8; 32]) {
        let kyber_pk_bytes = &pk[..KYBER_PK_LEN];
        let x25519_pk_bytes = &pk[KYBER_PK_LEN..KYBER_PK_LEN + X25519_PK_LEN];

        let kyber_pk =
            kyber768::PublicKey::from_bytes(kyber_pk_bytes).expect("invalid Kyber768 public key");

        let (kyber_ct, kyber_ss) = kyber768::encapsulate(&kyber_pk);

        let eph_sk = X25519StaticSecret::random_from_rng(rng);
        let eph_pk = X25519PublicKey::from(&eph_sk);
        let x25519_pk = X25519PublicKey::from(<[u8; 32]>::try_from(x25519_pk_bytes).unwrap());
        let x25519_ss = eph_sk.diffie_hellman(&x25519_pk);

        let mut ct = Vec::with_capacity(KYBER_CT_LEN + X25519_PK_LEN);
        ct.extend_from_slice(kyber_ct.as_bytes());
        ct.extend_from_slice(eph_pk.as_bytes());

        let mut ss = [0u8; 32];
        let mut hasher = blake3::Hasher::new();
        hasher.update(kyber_ss.as_bytes());
        hasher.update(x25519_ss.as_bytes());
        ss.copy_from_slice(hasher.finalize().as_bytes());

        (ct, ss)
    }

    fn decapsulate(&self, ct: &[u8], sk: &[u8]) -> AuthResult<[u8; 32]> {
        if ct.len() != Self::CT_LEN {
            return Err(AuthError::KemDecapsulation);
        }
        if sk.len() != KYBER_SK_LEN + X25519_SK_LEN {
            return Err(AuthError::InvalidKey);
        }

        let kyber_ct_bytes = &ct[..KYBER_CT_LEN];
        let x25519_eph_pk_bytes = &ct[KYBER_CT_LEN..];

        let kyber_sk = kyber768::SecretKey::from_bytes(&sk[..KYBER_SK_LEN])
            .map_err(|_| AuthError::InvalidKey)?;
        let kyber_ss = kyber768::decapsulate(
            &kyber768::Ciphertext::from_bytes(kyber_ct_bytes)
                .map_err(|_| AuthError::KemDecapsulation)?,
            &kyber_sk,
        );

        let x25519_sk_bytes: [u8; 32] = sk[KYBER_SK_LEN..KYBER_SK_LEN + X25519_SK_LEN]
            .try_into()
            .map_err(|_| AuthError::InvalidKey)?;
        let x25519_sk = X25519StaticSecret::from(x25519_sk_bytes);
        let x25519_eph_pk = X25519PublicKey::from(
            <[u8; 32]>::try_from(x25519_eph_pk_bytes).map_err(|_| AuthError::KemDecapsulation)?,
        );
        let x25519_ss = x25519_sk.diffie_hellman(&x25519_eph_pk);

        let mut ss = [0u8; 32];
        let mut hasher = blake3::Hasher::new();
        hasher.update(kyber_ss.as_bytes());
        hasher.update(x25519_ss.as_bytes());
        ss.copy_from_slice(hasher.finalize().as_bytes());

        Ok(ss)
    }
}
