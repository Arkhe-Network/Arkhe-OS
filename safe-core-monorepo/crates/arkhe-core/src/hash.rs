use crate::ArkheHash;

/// Computa hash BLAKE3 dos dados.
pub fn blake3_hash(data: &[u8]) -> ArkheHash {
    blake3::hash(data).into()
}

/// Converte hash para representação hex.
pub fn hash_to_hex(hash: &ArkheHash) -> String {
    hex::encode(hash)
}
