#![warn(missing_docs)]
#![deny(unsafe_code)]

pub mod backend;
pub mod error;
pub mod fs;
pub mod nodes;
pub mod path;

pub use backend::{FsBackend, MemoryBackend};
pub use error::{UnifiedFsError, UnifiedFsResult};
pub use fs::{AuditEvent, UnifiedFileSystem};
pub use nodes::{AclEntry, AclPermissions, FsNode, NodeMeta, NodeType};
pub use path::UnifiedPath;
