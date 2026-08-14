use crate::error::AuthResult;
use crate::key_hierarchy::KeyHierarchy;
use crate::types::{FastAead, NodeId};

#[derive(Clone, Copy, PartialEq, Eq)]
pub struct HeraldMessage {
    pub src_did: NodeId,
    pub dst_did: NodeId,
    pub timestamp_ns: u64,
    pub mode_idx: u8,
    pub herald_outcome: u8,
    pub burst_seq: u32,
    pub auth_tag: [u8; 16],
}

impl HeraldMessage {
    pub const WIRE_SIZE: usize = 96;

    pub fn to_bytes(&self) -> [u8; Self::WIRE_SIZE] {
        let mut buf = [0u8; Self::WIRE_SIZE];
        buf[0..33].copy_from_slice(&self.src_did.0);
        buf[33..66].copy_from_slice(&self.dst_did.0);
        buf[66..74].copy_from_slice(&self.timestamp_ns.to_le_bytes());
        buf[74] = self.mode_idx;
        buf[75] = self.herald_outcome;
        buf[76..80].copy_from_slice(&self.burst_seq.to_le_bytes());
        buf[80..96].copy_from_slice(&self.auth_tag);
        buf
    }

    pub fn from_bytes(buf: &[u8]) -> AuthResult<Self> {
        if buf.len() != Self::WIRE_SIZE {
            return Err(crate::error::AuthError::Deserialization);
        }
        let mut ts = [0u8; 8];
        ts.copy_from_slice(&buf[66..74]);
        let mut bs = [0u8; 4];
        bs.copy_from_slice(&buf[76..80]);
        let mut tag = [0u8; 16];
        tag.copy_from_slice(&buf[80..96]);
        Ok(Self {
            src_did: NodeId(
                buf[0..33]
                    .try_into()
                    .map_err(|_| crate::error::AuthError::Deserialization)?,
            ),
            dst_did: NodeId(
                buf[33..66]
                    .try_into()
                    .map_err(|_| crate::error::AuthError::Deserialization)?,
            ),
            timestamp_ns: u64::from_le_bytes(ts),
            mode_idx: buf[74],
            herald_outcome: buf[75],
            burst_seq: u32::from_le_bytes(bs),
            auth_tag: tag,
        })
    }

    pub fn aad(&self) -> [u8; 80] {
        let mut aad = [0u8; 80];
        aad[0..33].copy_from_slice(&self.src_did.0);
        aad[33..66].copy_from_slice(&self.dst_did.0);
        aad[66..74].copy_from_slice(&self.timestamp_ns.to_le_bytes());
        aad[74] = self.mode_idx;
        aad[75] = self.herald_outcome;
        aad[76..80].copy_from_slice(&self.burst_seq.to_le_bytes());
        aad
    }
}

impl core::fmt::Debug for HeraldMessage {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.debug_struct("HeraldMessage")
            .field("src", &self.src_did)
            .field("dst", &self.dst_did)
            .field("ts", &self.timestamp_ns)
            .field("mode", &self.mode_idx)
            .field("outcome", &self.herald_outcome)
            .field("seq", &self.burst_seq)
            .field("tag", &alloc::format!("{:02x?}", &self.auth_tag[..4]))
            .finish()
    }
}

pub struct FastPathAuth<A: FastAead> {
    pub key_hierarchy: KeyHierarchy,
    aead: A,
}

impl<A: FastAead> FastPathAuth<A> {
    pub fn new(key_hierarchy: KeyHierarchy, aead: A) -> Self {
        Self {
            key_hierarchy,
            aead,
        }
    }

    pub fn seal_herald(&mut self, msg: &mut HeraldMessage) -> AuthResult<()> {
        let nonce = self.key_hierarchy.tick()?;
        let aad = msg.aad();
        let mut plaintext = [];
        let tag = self
            .aead
            .seal(self.key_hierarchy.burst_key(), &nonce, &aad, &mut plaintext);
        msg.auth_tag = tag;
        Ok(())
    }

    pub fn verify_herald(&mut self, msg: &HeraldMessage) -> AuthResult<()> {
        let nonce = self.key_hierarchy.derive_nonce();
        let aad = msg.aad();
        let mut plaintext = [];
        self.aead.open(
            self.key_hierarchy.burst_key(),
            &nonce,
            &aad,
            &mut plaintext,
            &msg.auth_tag,
        )
    }
}
