#![cfg(target_os = "linux")]

use crate::caster::*;
use std::os::unix::io::{FromRawFd, IntoRawFd, RawFd};
use std::process::{Child, Command, Stdio};
use std::fs::File;

/// Gerencia o ciclo de vida do wireguard-go via linha de comando e controle do TUN FD.
pub struct WireGuardGoTunnel {
    wg_process: Option<Child>,
    tun_fd: Option<RawFd>,
    tun_name: String,
}

impl WireGuardGoTunnel {
    pub fn new(tun_name: &str) -> Self {
        Self {
            wg_process: None,
            tun_fd: None,
            tun_name: tun_name.to_string(),
        }
    }

    /// Cria o TUN device no Linux e retorna o FD
    fn create_tun_fd(_name: &str) -> Result<RawFd, u32> {
        Ok(0) // Stub
    }
}

impl OsTunnelProvider for WireGuardGoTunnel {
    fn setup_tunnel(&mut self, _iface_idx: usize, _pubkey: &[u8], _privkey: &[u8]) -> Result<(), u32> {
        let fd = Self::create_tun_fd(&self.tun_name)?;
        self.tun_fd = Some(fd);

        let fd_str = fd.to_string();
        let child = Command::new("wireguard-go")
            .arg("-f")
            .arg(&fd_str)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|_| 0x3191_0005)?;

        self.wg_process = Some(child);

        Ok(())
    }

    fn migrate_tunnel(&mut self, _new_iface_idx: usize) -> Result<(), u32> {
        Ok(())
    }

    fn teardown_tunnel(&mut self) -> Result<(), u32> {
        if let Some(mut child) = self.wg_process.take() {
            let _ = child.kill();
        }

        if let Some(fd) = self.tun_fd.take() {
            unsafe { libc::close(fd); }
        }

        Ok(())
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// BORINGTUN NATIVE TUNNEL
// ─────────────────────────────────────────────────────────────────────────────
// pub struct BoringtunNativeTunnel {
//     peer: boringtun::peer::Peer,
// }
//
// impl OsTunnelProvider for BoringtunNativeTunnel {
//     fn setup_tunnel(&mut self, _iface_idx: usize, _pubkey: &[u8], _privkey: &[u8]) -> Result<(), u32> {
//         Ok(())
//     }
//     fn migrate_tunnel(&mut self, _new_iface_idx: usize) -> Result<(), u32> { Ok(()) }
//     fn teardown_tunnel(&mut self) -> Result<(), u32> { Ok(()) }
// }
