//! ARKHE OS — Global Device Identifier (GDID)
//!
//! Identificador verificável de 32 bytes para hardware fisico. O layout e
//! deliberadamente fixo e sem alocacao para permanecer barato de derivar em
//! ambientes com poucos recursos (ex: nRF5x, MG24), mesmo que este crate em
//! si dependa de `std` por transitividade de `arkhe-core`.
//!
//! Formato binario:
//! - `[0]`: Version (0x01 = Ed25519, 0x02 = ML-DSA-65)
//! - `[1]`: Namespace (0x00 = Arkhe, 0x01 = Hubble, 0x02 = OEM)
//! - `[2..22]`: Hardware Hash (truncado de blake3, 20 bytes)
//! - `[22..26]`: Nonce do issuer (u32, big-endian)
//! - `[26..32]`: Reservado (zeros)

pub mod cert;
pub mod crl;
pub mod hubble;

pub use cert::{CapabilityBitmap, GdidCertificate, GdidError};
pub use crl::{CrlBundle, MerkleProof};
pub use hubble::GdidShort;

use core::fmt;
use serde::{Deserialize, Serialize};
use zeroize::Zeroize;

/// Identificador de dispositivo de 32 bytes.
///
/// `Zeroize` (sem `Drop`) e derivado para permitir apagar copias em buffers
/// sensiveis sob demanda; `Gdid` continua `Copy` pois nao e segredo em si
/// (o segredo e a chave privada correspondente, nunca representada aqui).
#[repr(C)]
#[derive(Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Zeroize)]
pub struct Gdid(pub [u8; 32]);

impl Gdid {
    /// Tamanho fixo do GDID.
    pub const SIZE: usize = 32;

    /// Namespace padrao do ARKHE.
    pub const NS_ARKHE: u8 = 0x00;
    /// Namespace para a rede Hubble.
    pub const NS_HUBBLE: u8 = 0x01;
    /// Namespace para fabricantes (OEMs).
    pub const NS_OEM: u8 = 0x02;

    /// Versao Ed25519.
    pub const VERSION_ED25519: u8 = 0x01;
    /// Versao ML-DSA-65 (pos-quantico).
    pub const VERSION_ML_DSA_65: u8 = 0x02;

    /// Cria um GDID a partir dos bytes brutos.
    ///
    /// # Seguranca
    /// Nao verifica se os bytes estao bem formados. Use [`Gdid::from_parts`]
    /// para construcao canonica.
    pub const fn from_raw(bytes: [u8; 32]) -> Self {
        Self(bytes)
    }

    /// Constroi um GDID de forma canonica.
    pub fn from_parts(version: u8, namespace: u8, hw_hash_truncated: &[u8; 20], nonce: u32) -> Self {
        let mut bytes = [0u8; 32];
        bytes[0] = version;
        bytes[1] = namespace;
        bytes[2..22].copy_from_slice(hw_hash_truncated);
        bytes[22..26].copy_from_slice(&nonce.to_be_bytes());
        // bytes[26..32] permanece 0x00 (reservado)
        Self(bytes)
    }

    /// Extrai o hardware hash truncado (20 bytes).
    pub fn hw_hash(&self) -> [u8; 20] {
        let mut out = [0u8; 20];
        out.copy_from_slice(&self.0[2..22]);
        out
    }

    /// Extrai o nonce do issuer.
    pub fn nonce(&self) -> u32 {
        u32::from_be_bytes([self.0[22], self.0[23], self.0[24], self.0[25]])
    }

    /// Extrai a versao.
    pub fn version(&self) -> u8 {
        self.0[0]
    }

    /// Extrai o namespace.
    pub fn namespace(&self) -> u8 {
        self.0[1]
    }

    /// Retorna os bytes brutos.
    pub const fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }

    /// Deriva o GDID a partir de um fingerprint de hardware completo (32 bytes).
    pub fn from_fingerprint(fingerprint: &[u8; 32], namespace: u8, nonce: u32) -> Self {
        let hash = blake3::hash(fingerprint);
        let mut hw_truncated = [0u8; 20];
        hw_truncated.copy_from_slice(&hash.as_bytes()[..20]);
        Self::from_parts(Self::VERSION_ED25519, namespace, &hw_truncated, nonce)
    }

    /// Deriva o fingerprint do dispositivo de forma deterministica e segura.
    ///
    /// Regras de privacidade: NAO inclui endereco MAC/IP, IMEI ou serial
    /// legivel. O hash e one-way (nao reversivel sem tabela do issuer).
    pub fn derive_fingerprint(cpu_id: &[u8], flash_uuid: &[u8], board_sku: &[u8]) -> [u8; 32] {
        let mut hasher = blake3::Hasher::new();
        hasher.update(b"arkhe-gdid-v1");
        hasher.update(cpu_id);
        hasher.update(flash_uuid);
        hasher.update(board_sku);
        hasher.finalize().into()
    }

    /// Codifica em Base58Check (string legivel).
    pub fn to_base58(&self) -> String {
        let mut payload = [0u8; 30]; // version + namespace + hash + nonce
        payload[0] = self.0[0];
        payload[1] = self.0[1];
        payload[2..22].copy_from_slice(&self.0[2..22]);
        payload[22..26].copy_from_slice(&self.0[22..26]);

        let checksum = blake3::hash(&payload);
        let mut final_buf = [0u8; 35]; // 1 prefixo + 30 payload + 4 checksum
        final_buf[0] = 0x01; // prefixo Base58Check
        final_buf[1..31].copy_from_slice(&payload);
        final_buf[31..35].copy_from_slice(&checksum.as_bytes()[..4]);

        bs58::encode(&final_buf).into_string()
    }
}

impl fmt::Debug for Gdid {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Gdid({})", self.to_base58())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn derivation_is_deterministic() {
        let fp = [7u8; 32];
        let a = Gdid::from_fingerprint(&fp, Gdid::NS_ARKHE, 100);
        let b = Gdid::from_fingerprint(&fp, Gdid::NS_ARKHE, 100);
        assert_eq!(a, b);
    }

    #[test]
    fn different_nonce_yields_different_gdid() {
        let fp = [7u8; 32];
        let a = Gdid::from_fingerprint(&fp, Gdid::NS_ARKHE, 100);
        let b = Gdid::from_fingerprint(&fp, Gdid::NS_ARKHE, 101);
        assert_ne!(a, b);
    }

    #[test]
    fn different_namespace_yields_different_gdid() {
        let fp = [7u8; 32];
        let a = Gdid::from_fingerprint(&fp, Gdid::NS_ARKHE, 100);
        let b = Gdid::from_fingerprint(&fp, Gdid::NS_HUBBLE, 100);
        assert_ne!(a, b);
    }

    #[test]
    fn accessors_roundtrip_through_from_parts() {
        let hw = [9u8; 20];
        let gdid = Gdid::from_parts(Gdid::VERSION_ED25519, Gdid::NS_OEM, &hw, 0xDEAD_BEEF);
        assert_eq!(gdid.version(), Gdid::VERSION_ED25519);
        assert_eq!(gdid.namespace(), Gdid::NS_OEM);
        assert_eq!(gdid.hw_hash(), hw);
        assert_eq!(gdid.nonce(), 0xDEAD_BEEF);
    }

    #[test]
    fn base58_encoding_is_stable_and_decodable() {
        let fp = [1u8; 32];
        let gdid = Gdid::from_fingerprint(&fp, Gdid::NS_ARKHE, 42);
        let encoded = gdid.to_base58();
        let decoded = bs58::decode(&encoded).into_vec().expect("valid base58");
        assert_eq!(decoded.len(), 35);
        assert_eq!(decoded[0], 0x01);
    }
}
