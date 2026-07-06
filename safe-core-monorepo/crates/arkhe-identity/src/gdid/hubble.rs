//! Formato curto de GDID (13 bytes) para payloads Hubble com banda limitada.

use super::Gdid;

/// Formato curto de 13 bytes para payloads Hubble.
///
/// O gateway mapeia este ID curto de volta para o [`Gdid`] completo usando
/// uma tabela local; a extracao aqui e apenas uma projecao dos campos, nao
/// uma derivacao reversivel.
///
/// Layout:
/// - `[0]`: prefixo Hubble (`0x48` = `'H'`)
/// - `[1]`: byte de versao do GDID original (o namespace nao e recodificado
///   aqui pois `GdidShort` so circula dentro do contexto Hubble, onde o
///   namespace ja e implicito)
/// - `[2..10]`: 8 bytes do hardware hash truncado
/// - `[10..13]`: 3 bytes superiores do nonce (32 bits -> 24 bits)
#[repr(C)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GdidShort(pub [u8; 13]);

impl GdidShort {
    /// Prefixo que identifica payloads Hubble.
    pub const PREFIX: u8 = 0x48;

    /// Mapeia de um GDID completo para 13 bytes.
    pub fn from_full(gdid: &Gdid) -> Self {
        let b = gdid.as_bytes();
        let mut short = [0u8; 13];
        short[0] = Self::PREFIX;
        short[1] = b[0]; // versao + namespace
        short[2..10].copy_from_slice(&b[2..10]); // 8 bytes do hash
        short[10..13].copy_from_slice(&b[22..25]); // 3 bytes superiores do nonce
        Self(short)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn short_projection_preserves_prefix_version_and_hash() {
        let hw = [9u8; 20];
        let full = Gdid::from_parts(Gdid::VERSION_ED25519, Gdid::NS_HUBBLE, &hw, 0x1122_3344);
        let short = GdidShort::from_full(&full);

        assert_eq!(short.0[0], GdidShort::PREFIX);
        assert_eq!(short.0[1], full.as_bytes()[0]);
        assert_eq!(&short.0[2..10], &full.as_bytes()[2..10]);
        assert_eq!(&short.0[10..13], &full.as_bytes()[22..25]);
    }
}
