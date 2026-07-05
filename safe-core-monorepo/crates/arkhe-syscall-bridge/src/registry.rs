use crate::error::{BridgeError, BridgeResult};
use crate::mapping::{SyscallCategory, SyscallMapping, SyscallSide};
use std::collections::HashMap;

/// Registro de mapeamentos de syscalls.
pub struct SyscallRegistry {
    /// Mapeamentos indexados por `(from_side, from_number)`.
    mappings: HashMap<(SyscallSide, u32), SyscallMapping>,
}

impl SyscallRegistry {
    /// Cria registro vazio.
    pub fn new() -> Self {
        Self {
            mappings: HashMap::new(),
        }
    }

    /// Cria registro com mapeamentos padrão Linux↔Windows.
    pub fn with_defaults() -> Self {
        let mut reg = Self::new();
        reg.load_defaults();
        reg
    }

    /// Registra um mapeamento.
    pub fn register(&mut self, mapping: SyscallMapping) {
        let key = (mapping.from_side, mapping.from_number);
        self.mappings.insert(key, mapping);
    }

    /// Resolve um mapeamento.
    pub fn resolve(
        &self,
        from_side: SyscallSide,
        from_number: u32,
        to_side: SyscallSide,
    ) -> BridgeResult<&SyscallMapping> {
        let mapping = self
            .mappings
            .get(&(from_side, from_number))
            .ok_or(BridgeError::SyscallNotFound {
                side: from_side.to_string(),
                number: from_number,
            })?;

        if mapping.to_side != to_side {
            return Err(BridgeError::NoMapping {
                from_side: from_side.to_string(),
                from_number,
                to_side: to_side.to_string(),
            });
        }

        match mapping.category {
            SyscallCategory::Blocked => Err(BridgeError::Blocked {
                reason: mapping.notes.clone(),
            }),
            _ => Ok(mapping),
        }
    }

    /// Lista todos os mapeamentos para um lado específico.
    pub fn list_by_from_side(&self, side: SyscallSide) -> Vec<&SyscallMapping> {
        self.mappings
            .iter()
            .filter(|((s, _), _)| *s == side)
            .map(|(_, m)| m)
            .collect()
    }

    /// Lista mapeamentos por categoria.
    pub fn list_by_category(&self, category: SyscallCategory) -> Vec<&SyscallMapping> {
        self.mappings
            .iter()
            .filter(|(_, m)| m.category == category)
            .map(|(_, m)| m)
            .collect()
    }

    /// Conta mapeamentos por categoria.
    pub fn count_by_category(&self) -> HashMap<SyscallCategory, usize> {
        let mut counts = HashMap::new();
        for m in self.mappings.values() {
            *counts.entry(m.category).or_insert(0) += 1;
        }
        counts
    }

    /// Carrega mapeamentos padrão.
    ///
    /// Estes são exemplos representativos — uma implementação completa
    /// cobriria centenas de syscalls.
    fn load_defaults(&mut self) {
        use SyscallSide::*;

        // ── Linux → Windows (seletivo) ──
        // read → ReadFile
        self.register(SyscallMapping::translate(
            "read/ReadFile",
            Linux, 0, // SYS_read
            Windows, 0x0F, // NtReadFile (simplificado)
            vec![
                crate::mapping::SyscallParam {
                    name: "fd".into(), type_name: "int".into(),
                    direction: crate::mapping::ParamDirection::In,
                    needs_translation: true, // fd → HANDLE
                },
                crate::mapping::SyscallParam {
                    name: "buf".into(), type_name: "void*".into(),
                    direction: crate::mapping::ParamDirection::Out,
                    needs_translation: false,
                },
                crate::mapping::SyscallParam {
                    name: "count".into(), type_name: "size_t".into(),
                    direction: crate::mapping::ParamDirection::In,
                    needs_translation: false,
                },
            ],
            "fd→HANDLE translation required",
        ));

        // write → WriteFile
        self.register(SyscallMapping::translate(
            "write/WriteFile",
            Linux, 1, // SYS_write
            Windows, 0x10, // NtWriteFile
            vec![
                crate::mapping::SyscallParam {
                    name: "fd".into(), type_name: "int".into(),
                    direction: crate::mapping::ParamDirection::In,
                    needs_translation: true,
                },
            ],
            "fd→HANDLE translation required",
        ));

        // openat → NtCreateFile
        self.register(SyscallMapping::translate(
            "openat/NtCreateFile",
            Linux, 257, // SYS_openat
            Windows, 0x11, // NtCreateFile
            vec![
                crate::mapping::SyscallParam {
                    name: "pathname".into(), type_name: "const char*".into(),
                    direction: crate::mapping::ParamDirection::In,
                    needs_translation: true, // path format
                },
                crate::mapping::SyscallParam {
                    name: "flags".into(), type_name: "int".into(),
                    direction: crate::mapping::ParamDirection::In,
                    needs_translation: true, // O_RDONLY→GENERIC_READ
                },
            ],
            "Path format, flags, and mode require full translation",
        ));

        // mmap → VirtualAlloc (emulação necessária)
        self.register(SyscallMapping {
            name: "mmap/VirtualAlloc".into(),
            from_number: 9, // SYS_mmap
            to_number: 0x12, // NtAllocateVirtualMemory
            from_side: Linux,
            to_side: Windows,
            category: SyscallCategory::Emulate,
            params: vec![],
            notes: "mmap semantics differ significantly from VirtualAlloc".into(),
        });

        // clone → bloqueado (process fork não existe no Windows)
        self.register(SyscallMapping::blocked(
            "clone",
            Linux, 56, // SYS_clone
            "fork()/clone() has no Windows equivalent — use threads or processes",
        ));

        // ── Windows → Linux (seletivo) ──
        // CreateFileW → openat
        self.register(SyscallMapping::translate(
            "CreateFileW/openat",
            Windows, 0x11, // NtCreateFile
            Linux, 257, // SYS_openat
            vec![
                crate::mapping::SyscallParam {
                    name: "lpFileName".into(), type_name: "LPCWSTR".into(),
                    direction: crate::mapping::ParamDirection::In,
                    needs_translation: true, // wide→UTF-8 path
                },
                crate::mapping::SyscallParam {
                    name: "dwDesiredAccess".into(), type_name: "DWORD".into(),
                    direction: crate::mapping::ParamDirection::In,
                    needs_translation: true, // GENERIC_READ→O_RDONLY
                },
            ],
            "Wide string path and access flags need translation",
        ));

        // CreateProcess → fork+exec (emulação)
        self.register(SyscallMapping {
            name: "CreateProcess/fork+exec".into(),
            from_number: 0x20, // NtCreateUserProcess
            to_number: 0, // N/A
            from_side: Windows,
            to_side: Linux,
            category: SyscallCategory::Emulate,
            params: vec![],
            notes: "CreateProcess → fork() + execve() emulation".into(),
        });
    }
}

impl Default for SyscallRegistry {
    fn default() -> Self {
        Self::with_defaults()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolve_linux_to_windows() {
        let reg = SyscallRegistry::with_defaults();
        let mapping = reg.resolve(SyscallSide::Linux, 0, SyscallSide::Windows).unwrap();
        assert_eq!(mapping.name, "read/ReadFile");
        assert_eq!(mapping.category, SyscallCategory::Translate);
    }

    #[test]
    fn resolve_windows_to_linux() {
        let reg = SyscallRegistry::with_defaults();
        let mapping = reg.resolve(SyscallSide::Windows, 0x11, SyscallSide::Linux).unwrap();
        assert_eq!(mapping.name, "CreateFileW/openat");
    }

    #[test]
    fn blocked_syscall_returns_error() {
        let reg = SyscallRegistry::with_defaults();
        let result = reg.resolve(SyscallSide::Linux, 56, SyscallSide::Windows);
        assert!(matches!(result, Err(BridgeError::Blocked { .. })));
    }

    #[test]
    fn unknown_syscall_not_found() {
        let reg = SyscallRegistry::with_defaults();
        let result = reg.resolve(SyscallSide::Linux, 9999, SyscallSide::Windows);
        assert!(matches!(result, Err(BridgeError::SyscallNotFound { .. })));
    }

    #[test]
    fn wrong_target_side_no_mapping() {
        let reg = SyscallRegistry::with_defaults();
        // read (0) está mapeado Linux→Windows, não Linux→Linux
        let result = reg.resolve(SyscallSide::Linux, 0, SyscallSide::Linux);
        assert!(matches!(result, Err(BridgeError::NoMapping { .. })));
    }

    #[test]
    fn count_by_category() {
        let reg = SyscallRegistry::with_defaults();
        let counts = reg.count_by_category();
        assert!(counts.get(&SyscallCategory::Translate).unwrap_or(&0) > &0);
        assert!(counts.get(&SyscallCategory::Blocked).unwrap_or(&0) > &0);
        assert!(counts.get(&SyscallCategory::Emulate).unwrap_or(&0) > &0);
    }

    #[test]
    fn list_by_side() {
        let reg = SyscallRegistry::with_defaults();
        let linux_mappings = reg.list_by_from_side(SyscallSide::Linux);
        assert!(linux_mappings.len() >= 4); // read, write, openat, mmap, clone

        let windows_mappings = reg.list_by_from_side(SyscallSide::Windows);
        assert!(windows_mappings.len() >= 2); // CreateFileW, CreateProcess
    }

    #[test]
    fn custom_registration() {
        let mut reg = SyscallRegistry::new();
        reg.register(SyscallMapping::safe(
            "custom",
            SyscallSide::Linux,
            999,
            SyscallSide::Windows,
            888,
        ));

        let mapping = reg.resolve(SyscallSide::Linux, 999, SyscallSide::Windows).unwrap();
        assert_eq!(mapping.name, "custom");
        assert_eq!(mapping.category, SyscallCategory::Safe);
    }
}
