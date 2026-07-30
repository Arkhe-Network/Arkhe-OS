#[cfg(feature = "mcp")]
pub mod mcp_impl {
    use crate::tools;
    use crate::state::BridgeState;
    use rmcp::{ServerHandler, ServiceExt, transport::stdio};
    use rmcp::{tool, tool_router};
    use std::sync::Arc;
    use tracing::info;
    use serde::{Deserialize, Serialize};

    #[derive(Clone)]
    pub struct SafeCoreMcpServer {
        state: Arc<BridgeState>,
    }

    impl SafeCoreMcpServer {
        pub fn new(state: Arc<BridgeState>) -> Self {
            Self { state }
        }

        pub async fn run_stdio(self) -> Result<(), Box<dyn std::error::Error>> {
            info!("MCP server iniciando no modo stdio");
            self.serve(stdio()).await?;
            Ok(())
        }
    }

    impl ServerHandler for SafeCoreMcpServer {}

    #[derive(Debug, Clone, Serialize, Deserialize)]
    pub struct EnforceActionParams {
        action: String,
        context: serde_json::Value,
    }

    #[tool_router]
    impl SafeCoreMcpServer {
        #[tool(description = "Check if an action is ethically permitted")]
        pub async fn enforce_action(
            &self,
            action: String,
            context: serde_json::Value,
        ) -> Result<serde_json::Value, String> {
            let result = tools::enforce_action(&self.state, &action, &context)
                .await
                .map_err(|e| e.to_string())?;
            serde_json::to_value(&result).map_err(|e| e.to_string())
        }

        #[tool(description = "List all recorded ethics violations")]
        pub async fn get_violations(
            &self,
        ) -> Result<serde_json::Value, String> {
            let resp = tools::get_violations(&self.state).await;
            serde_json::to_value(&resp).map_err(|e| e.to_string())
        }

        #[tool(description = "Clear all recorded ethics violations")]
        pub async fn clear_violations(
            &self,
        ) -> Result<serde_json::Value, String> {
            let result = tools::clear_violations(&self.state).await;
            Ok(result)
        }

        #[tool(description = "List all safety invariants")]
        pub async fn list_invariants(
            &self,
        ) -> Result<serde_json::Value, String> {
            let resp = tools::list_invariants(&self.state);
            serde_json::to_value(&resp).map_err(|e| e.to_string())
        }

        #[tool(description = "Export safety invariants")]
        pub async fn export_invariants(
            &self,
        ) -> Result<serde_json::Value, String> {
            let result = tools::export_invariants(&self.state)
                .await
                .map_err(|e| e.to_string())?;
            Ok(result)
        }

        #[tool(description = "Health check")]
        pub async fn health(
            &self,
        ) -> Result<serde_json::Value, String> {
            let resp = tools::health_check(&self.state).await;
            serde_json::to_value(&resp).map_err(|e| e.to_string())
        }
    }
}

#[cfg(not(feature = "mcp"))]
pub mod mcp_impl {
    pub struct SafeCoreMcpServer;

    impl SafeCoreMcpServer {
        pub fn new(_: std::sync::Arc<crate::state::BridgeState>) -> Self {
            Self
        }

        pub async fn run_stdio(self) -> Result<(), Box<dyn std::error::Error>> {
            Err("MCP não disponível. Compile com: cargo build -p safe-core-bridge --features mcp".into())
        }
    }
}

pub use mcp_impl::SafeCoreMcpServer;
