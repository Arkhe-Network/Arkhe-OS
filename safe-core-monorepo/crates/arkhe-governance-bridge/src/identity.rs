use serde::{Deserialize, Serialize};

/// Plataforma de origem da identidade.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum PlatformSide {
    Windows,
    Linux,
    Arkhe,
}

impl std::fmt::Display for PlatformSide {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PlatformSide::Windows => write!(f, "windows"),
            PlatformSide::Linux => write!(f, "linux"),
            PlatformSide::Arkhe => write!(f, "arkhe"),
        }
    }
}

/// Identidade nativa de uma plataforma.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlatformIdentity {
    /// Plataforma.
    pub side: PlatformSide,

    /// Identificador nativo:
    /// - Windows: SID (ex: "S-1-5-21-3623811015-3361044348-30300820-1001")
    /// - Linux: "uid:1000:gid:1000"
    /// - Arkhe: DID (ex: "did:arkhe:user-abc")
    pub identifier: String,

    /// Nome de exibição (opcional).
    pub display_name: Option<String>,

    /// Se a identidade está ativa.
    pub active: bool,

    /// Metadados adicionais.
    pub extra: serde_json::Value,
}

impl PlatformIdentity {
    /// Cria identidade Windows (SID).
    pub fn windows_sid(sid: &str, display_name: Option<&str>) -> Self {
        Self {
            side: PlatformSide::Windows,
            identifier: sid.to_string(),
            display_name: display_name.map(String::from),
            active: true,
            extra: serde_json::Value::Null,
        }
    }

    /// Cria identidade Linux (UID:GID).
    pub fn linux_uid_gid(uid: u32, gid: u32, display_name: Option<&str>) -> Self {
        Self {
            side: PlatformSide::Linux,
            identifier: format!("uid:{}:gid:{}", uid, gid),
            display_name: display_name.map(String::from),
            active: true,
            extra: serde_json::json!({"uid": uid, "gid": gid}),
        }
    }

    /// Cria identidade Arkhe (DID).
    pub fn arkhe_did(did: &str, display_name: Option<&str>) -> Self {
        Self {
            side: PlatformSide::Arkhe,
            identifier: did.to_string(),
            display_name: display_name.map(String::from),
            active: true,
            extra: serde_json::Value::Null,
        }
    }

    /// Extrai UID se for identidade Linux.
    pub fn linux_uid(&self) -> Option<u32> {
        if self.side != PlatformSide::Linux {
            return None;
        }
        self.extra
            .get("uid")
            .and_then(|v| v.as_u64())
            .map(|v| v as u32)
    }

    /// Extrai GID se for identidade Linux.
    pub fn linux_gid(&self) -> Option<u32> {
        if self.side != PlatformSide::Linux {
            return None;
        }
        self.extra
            .get("gid")
            .and_then(|v| v.as_u64())
            .map(|v| v as u32)
    }
}
