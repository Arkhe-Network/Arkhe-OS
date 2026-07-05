use serde::{Deserialize, Serialize};

/// Lado da chamada de sistema.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum SyscallSide {
    Linux,
    Windows,
}

impl std::fmt::Display for SyscallSide {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SyscallSide::Linux => write!(f, "linux"),
            SyscallSide::Windows => write!(f, "windows"),
        }
    }
}

/// Categoria de risco de uma syscall.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SyscallCategory {
    /// Segura — pode ser mapeada diretamente.
    Safe,
    /// Requer tradução de argumentos.
    Translate,
    /// Requer emulação completa no userspace.
    Emulate,
    /// Bloqueada — não pode ser mapeada.
    Blocked,
    /// Delegada ao sandbox WASM.
    Sandbox,
}

/// Mapeamento individual de syscall.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyscallMapping {
    /// Nome da syscall.
    pub name: String,

    /// Número no lado de origem.
    pub from_number: u32,

    /// Número no lado de destino.
    pub to_number: u32,

    /// Lado de origem.
    pub from_side: SyscallSide,

    /// Lado de destino.
    pub to_side: SyscallSide,

    /// Categoria de risco.
    pub category: SyscallCategory,

    /// Nomes dos parâmetros (para tradução).
    pub params: Vec<SyscallParam>,

    /// Notas sobre a tradução.
    pub notes: String,
}

/// Parâmetro de syscall.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyscallParam {
    pub name: String,
    pub type_name: String,
    pub direction: ParamDirection,
    /// Se este parâmetro precisa de tradução (ex: handle → fd).
    pub needs_translation: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ParamDirection {
    In,
    Out,
    InOut,
}

impl SyscallMapping {
    /// Cria mapeamento seguro (1:1 direto).
    pub fn safe(
        name: &str,
        from_side: SyscallSide,
        from_number: u32,
        to_side: SyscallSide,
        to_number: u32,
    ) -> Self {
        Self {
            name: name.to_string(),
            from_number,
            to_number,
            from_side,
            to_side,
            category: SyscallCategory::Safe,
            params: Vec::new(),
            notes: String::new(),
        }
    }

    /// Cria mapeamento que requer tradução.
    pub fn translate(
        name: &str,
        from_side: SyscallSide,
        from_number: u32,
        to_side: SyscallSide,
        to_number: u32,
        params: Vec<SyscallParam>,
        notes: &str,
    ) -> Self {
        Self {
            name: name.to_string(),
            from_number,
            to_number,
            from_side,
            to_side,
            category: SyscallCategory::Translate,
            params,
            notes: notes.to_string(),
        }
    }

    /// Cria mapeamento bloqueado.
    pub fn blocked(
        name: &str,
        from_side: SyscallSide,
        from_number: u32,
        reason: &str,
    ) -> Self {
        Self {
            name: name.to_string(),
            from_number,
            to_number: 0,
            from_side,
            to_side: from_side, // irrelevante
            category: SyscallCategory::Blocked,
            params: Vec::new(),
            notes: reason.to_string(),
        }
    }
}
