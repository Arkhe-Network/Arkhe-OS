//! Tradução de caminhos entre namespaces Windows e Linux.
//!
//! Regras:
//! - Linux: `/home/user/docs/file.txt`
//! - Windows: `C:\Users\user\docs\file.txt`
//! - Interno (unified): `ufs://home/user/docs/file.txt` (platform-agnostic)

use crate::error::{UnifiedFsError, UnifiedFsResult};
use std::path::{Component, Path, PathBuf};

/// Separador interno unificado (sempre `/`).
const UFS_SEPARATOR: char = '/';

/// Caminho unificado — representação platform-agnostic.
///
/// Internamente usa sempre `/` como separador, independente do SO hospedeiro.
/// Converte para o formato nativo quando necessário.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct UnifiedPath {
    /// Componentes do caminho (sem separadores iniciais/finais).
    /// Ex: `["home", "user", "docs"]` para `/home/user/docs/`
    components: Vec<String>,
    /// Se é absoluto (começa com `/`).
    absolute: bool,
}

impl UnifiedPath {
    /// Cria a partir de componentes.
    pub fn from_components(components: Vec<String>, absolute: bool) -> Self {
        // Normalizar: remover `.` e `..`
        let mut normalized = Vec::new();
        for c in &components {
            match c.as_str() {
                "." => continue,
                ".." => {
                    if !normalized.is_empty() {
                        normalized.pop();
                    }
                }
                "" => continue,
                other => normalized.push(other.to_string()),
            }
        }
        Self {
            components: normalized,
            absolute,
        }
    }

    /// Parse de caminho Linux (`/home/user/file.txt`).
    pub fn from_linux(path: &str) -> UnifiedFsResult<Self> {
        Self::validate_no_traversal(path)?;
        let path = Path::new(path);

        let absolute = path.has_root();
        let components: Vec<String> = path
            .components()
            .filter(|c| matches!(c, Component::Normal(_)))
            .filter_map(|c| c.as_os_str().to_str().map(String::from))
            .collect();

        Ok(Self::from_components(components, absolute))
    }

    /// Parse de caminho Windows (`C:\Users\user\file.txt`).
    pub fn from_windows(path: &str) -> UnifiedFsResult<Self> {
        Self::validate_no_traversal(path)?;
        // Remove prefixo de drive (C:, D:, etc.)
        let path = path.replace('\\', "/");
        let path = path
            .strip_prefix(|c: char| c.is_ascii_alphabetic())
            .unwrap_or(&path);
        let path = path.strip_prefix(':').unwrap_or(&path);
        let path = path.trim_start_matches('/');

        // Verificar se é UNC path (\\server\share\...)
        // Para simplificação, tratamos como caminho absoluto sem o prefixo

        let components: Vec<String> = path
            .split('/')
            .filter(|s| !s.is_empty())
            .map(String::from)
            .collect();

        Ok(Self::from_components(components, true))
    }

    /// Parse de caminho interno (`ufs://home/user/file.txt`).
    pub fn from_ufs(path: &str) -> UnifiedFsResult<Self> {
        let path = path.strip_prefix("ufs://").unwrap_or(path);
        Self::from_linux(path)
    }

    /// Converte para caminho Linux.
    pub fn to_linux(&self) -> String {
        let mut s = String::new();
        if self.absolute {
            s.push('/');
        }
        s.push_str(&self.components.join("/"));
        s
    }

    /// Converte para caminho Windows.
    pub fn to_windows(&self, drive: Option<&str>) -> String {
        let prefix = drive.unwrap_or("C");
        let mut s = format!("{}:", prefix);
        if self.absolute {
            s.push('\\');
        }
        s.push_str(&self.components.join("\\"));
        s
    }

    /// Converte para caminho interno UFS.
    pub fn to_ufs(&self) -> String {
        format!("ufs://{}", self.components.join("/"))
    }

    /// Nome do arquivo (último componente) ou `None` se vazio.
    pub fn file_name(&self) -> Option<&str> {
        self.components.last().map(|s| s.as_str())
    }

    /// Diretório pai.
    pub fn parent(&self) -> Option<UnifiedPath> {
        if self.components.is_empty() {
            return None;
        }
        let mut parent_components = self.components.clone();
        parent_components.pop();
        Some(UnifiedPath {
            components: parent_components,
            absolute: self.absolute,
        })
    }

    /// Adiciona sufixo ao caminho.
    pub fn join(&self, segment: &str) -> UnifiedFsResult<Self> {
        if segment.contains("..") || segment.contains('\0') {
            return Err(UnifiedFsError::InvalidPath {
                path: segment.to_string(),
                reason: "contains .. or null byte".into(),
            });
        }
        let mut components = self.components.clone();
        for part in segment.split('/').filter(|s| !s.is_empty()) {
            components.push(part.to_string());
        }
        Ok(Self {
            components,
            absolute: self.absolute,
        })
    }

    /// Profundidade do caminho (número de componentes).
    pub fn depth(&self) -> usize {
        self.components.len()
    }

    /// É caminho raiz?
    pub fn is_root(&self) -> bool {
        self.absolute && self.components.is_empty()
    }

    /// Extensão do arquivo (sem o ponto).
    pub fn extension(&self) -> Option<&str> {
        self.file_name()?.rsplit_once('.').map(|(_, ext)| ext)
    }

    /// Verifica se não há path traversal.
    fn validate_no_traversal(path: &str) -> UnifiedFsResult<()> {
        if path.contains("..") {
            return Err(UnifiedFsError::PathTraversal {
                path: path.to_string(),
            });
        }
        if path.contains('\0') {
            return Err(UnifiedFsError::InvalidPath {
                path: path.to_string(),
                reason: "null byte".into(),
            });
        }
        Ok(())
    }

    /// Converte para `std::path::PathBuf` nativo.
    pub fn to_native_path(&self) -> PathBuf {
        let s = if cfg!(windows) {
            self.to_windows(None)
        } else {
            self.to_linux()
        };
        PathBuf::from(s)
    }
}

impl std::fmt::Display for UnifiedPath {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.to_ufs())
    }
}

impl From<&str> for UnifiedPath {
    fn from(s: &str) -> Self {
        if s.starts_with("ufs://") {
            Self::from_ufs(s).expect("invalid UFS path")
        } else if s.contains('\\') || s.contains(':') {
            Self::from_windows(s).expect("invalid Windows path")
        } else {
            Self::from_linux(s).expect("invalid Linux path")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn linux_absolute() {
        let p = UnifiedPath::from_linux("/home/user/docs/file.txt").unwrap();
        assert!(p.absolute);
        assert_eq!(p.components, vec!["home", "user", "docs", "file.txt"]);
        assert_eq!(p.file_name(), Some("file.txt"));
        assert_eq!(p.extension(), Some("txt"));
        assert_eq!(p.to_linux(), "/home/user/docs/file.txt");
    }

    #[test]
    fn linux_relative() {
        let p = UnifiedPath::from_linux("docs/file.txt").unwrap();
        assert!(!p.absolute);
        assert_eq!(p.to_linux(), "docs/file.txt");
    }

    #[test]
    fn windows_absolute() {
        let p = UnifiedPath::from_windows(r"C:\Users\user\docs\file.txt").unwrap();
        assert!(p.absolute);
        assert_eq!(p.components, vec!["Users", "user", "docs", "file.txt"]);
        assert_eq!(p.to_windows(Some("C")), r"C:\Users\user\docs\file.txt");
    }

    #[test]
    fn windows_to_linux() {
        let p = UnifiedPath::from_windows(r"C:\Users\user\file.txt").unwrap();
        // Não é um mapeamento perfeito (Users ≠ home), mas a conversão é consistente
        assert_eq!(p.to_linux(), "/Users/user/file.txt");
    }

    #[test]
    fn roundtrip_ufs() {
        let original = "/home/user/docs/file.txt";
        let p = UnifiedPath::from_linux(original).unwrap();
        let ufs = p.to_ufs();
        let p2 = UnifiedPath::from_ufs(&ufs).unwrap();
        assert_eq!(p, p2);
        assert_eq!(p2.to_linux(), original);
    }

    #[test]
    fn parent() {
        let p = UnifiedPath::from_linux("/home/user/docs/file.txt").unwrap();
        let parent = p.parent().unwrap();
        assert_eq!(parent.to_linux(), "/home/user/docs");

        let parent2 = parent.parent().unwrap();
        assert_eq!(parent2.to_linux(), "/home/user");
    }

    #[test]
    fn parent_of_root_is_none() {
        let root = UnifiedPath::from_linux("/").unwrap();
        assert!(root.parent().is_none());
    }

    #[test]
    fn join() {
        let p = UnifiedPath::from_linux("/home/user").unwrap();
        let joined = p.join("docs/file.txt").unwrap();
        assert_eq!(joined.to_linux(), "/home/user/docs/file.txt");
    }

    #[test]
    fn join_rejects_traversal() {
        let p = UnifiedPath::from_linux("/home/user").unwrap();
        let result = p.join("../etc/passwd");
        assert!(result.is_err());
    }

    #[test]
    fn path_traversal_rejected() {
        assert!(UnifiedPath::from_linux("/home/../etc/passwd").is_err());
        assert!(UnifiedPath::from_windows(r"C:\Users\..\Windows\System32").is_err());
    }

    #[test]
    fn null_byte_rejected() {
        assert!(UnifiedPath::from_linux("/home/user/file\0.txt").is_err());
    }

    #[test]
    fn dot_normalized() {
        let p = UnifiedPath::from_linux("/home/./user/./docs/.").unwrap();
        assert_eq!(p.components, vec!["home", "user", "docs"]);
    }

    #[test]
    fn depth() {
        let p = UnifiedPath::from_linux("/a/b/c").unwrap();
        assert_eq!(p.depth(), 3);
        let root = UnifiedPath::from_linux("/").unwrap();
        assert_eq!(root.depth(), 0);
    }

    #[test]
    fn is_root() {
        assert!(UnifiedPath::from_linux("/").unwrap().is_root());
        assert!(!UnifiedPath::from_linux("/home").unwrap().is_root());
        assert!(!UnifiedPath::from_linux("relative").unwrap().is_root());
    }

    #[test]
    fn from_str_trait() {
        let p: UnifiedPath = "/home/user/file.txt".into();
        assert_eq!(p.to_linux(), "/home/user/file.txt");

        let p2: UnifiedPath = r"C:\Users\file.txt".into();
        assert_eq!(p2.to_windows(Some("C")), r"C:\Users\file.txt");

        let p3: UnifiedPath = "ufs://home/user".into();
        assert_eq!(p3.to_ufs(), "ufs://home/user");
    }

    #[test]
    fn unc_path() {
        let p = UnifiedPath::from_windows(r"\\server\share\file.txt").unwrap();
        // UNC: remove \\ prefix, treat as absolute
        assert!(p.absolute);
        assert_eq!(p.components, vec!["server", "share", "file.txt"]);
    }
}
