use crate::error::{AuthError, AuthResult};
use alloc::vec::Vec;
use hkdf::Hkdf;
use sha3::Sha3_256;
use zeroize::{Zeroize, ZeroizeOnDrop};

#[derive(Clone, Zeroize, ZeroizeOnDrop)]
pub struct KeyHierarchy {
    root_secret: [u8; 32],
    session_key: [u8; 32],
    burst_key: [u8; 32],
    session_counter: u64,
    pub burst_counter: u64,
    pub msg_counter: u64,
}

impl KeyHierarchy {
    pub const MAX_MSGS_PER_BURST: u64 = 100_000;

    pub fn from_xwing_shared_secret(ss: [u8; 32]) -> AuthResult<Self> {
        let mut session_key = [0u8; 32];
        let mut burst_key = [0u8; 32];

        hkdf_expand(&ss, b"arkhe-quantum-auth-session-v1", &mut session_key)?;
        hkdf_expand(&session_key, b"arkhe-quantum-auth-burst-v1", &mut burst_key)?;

        Ok(Self {
            root_secret: ss,
            session_key,
            burst_key,
            session_counter: 0,
            burst_counter: 0,
            msg_counter: 0,
        })
    }

    pub fn rotate_burst(&mut self) -> AuthResult<()> {
        self.burst_counter = self
            .burst_counter
            .checked_add(1)
            .ok_or(AuthError::CounterExhausted)?;

        let mut new_burst = [0u8; 32];
        let info = make_info_string("burst", self.burst_counter);
        hkdf_expand(&self.session_key, &info, &mut new_burst)?;

        self.burst_key.zeroize();
        self.burst_key = new_burst;
        self.msg_counter = 0;
        Ok(())
    }

    pub fn rotate_session(&mut self) -> AuthResult<()> {
        self.session_counter = self
            .session_counter
            .checked_add(1)
            .ok_or(AuthError::CounterExhausted)?;

        let mut new_session = [0u8; 32];
        let info = make_info_string("session", self.session_counter);
        hkdf_expand(&self.root_secret, &info, &mut new_session)?;

        self.session_key.zeroize();
        self.session_key = new_session;
        self.burst_counter = 0;
        self.rotate_burst()
    }

    pub fn derive_nonce(&self) -> [u8; 12] {
        let mut nonce = [0u8; 12];
        nonce[0..8].copy_from_slice(&self.msg_counter.to_le_bytes());
        nonce[8..12].copy_from_slice(&(self.burst_counter as u32).to_le_bytes());
        nonce
    }

    pub fn tick(&mut self) -> AuthResult<[u8; 12]> {
        self.msg_counter = self
            .msg_counter
            .checked_add(1)
            .ok_or(AuthError::CounterExhausted)?;

        if self.msg_counter >= Self::MAX_MSGS_PER_BURST {
            self.rotate_burst()?;
        }
        Ok(self.derive_nonce())
    }

    pub fn burst_key(&self) -> &[u8; 32] {
        &self.burst_key
    }

    pub fn session_key(&self) -> &[u8; 32] {
        &self.session_key
    }
}

fn hkdf_expand(prk: &[u8], info: &[u8], okm: &mut [u8]) -> AuthResult<()> {
    let hk = Hkdf::<Sha3_256>::new(None, prk);
    hk.expand(info, okm).map_err(|_| AuthError::KeyDerivation)
}

fn make_info_string(domain: &str, counter: u64) -> Vec<u8> {
    let mut buf = alloc::vec::Vec::with_capacity(48);
    buf.extend_from_slice(b"arkhe:");
    buf.extend_from_slice(domain.as_bytes());
    buf.push(b':');
    let mut tmp = [0u8; 20];
    let mut n = counter;
    for i in (0..20).rev() {
        tmp[i] = b'0' + (n % 10) as u8;
        n /= 10;
    }
    buf.extend_from_slice(&tmp);
    buf
}
