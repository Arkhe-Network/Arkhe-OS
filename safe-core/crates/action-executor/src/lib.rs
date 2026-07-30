//! action-executor — Os Músculos
//!
//! ToolExecutor com isolamento real via fork+execvp+Landlock

pub mod executor;
pub mod sandbox;
pub mod gate;
pub mod error;
pub mod tools;

pub use executor::ToolExecutor;
pub use sandbox::{SandboxExecutor, ExecutionResult};
pub use gate::{SecurityGate, ExecutionGate};
pub use error::ExecError;
pub use tools::{Tool, ToolResult, ShellTool, HttpTool, PythonTool};
