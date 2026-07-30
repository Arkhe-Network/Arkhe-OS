use std::process::{Child, Command};
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::info;

pub struct RemixRuntime {
    process: Arc<Mutex<Option<Child>>>,
    port: u16,
    workspace: String,
}

impl RemixRuntime {
    pub fn new(port: u16, workspace: String) -> Self {
        Self {
            process: Arc::new(Mutex::new(None)),
            port,
            workspace,
        }
    }

    pub async fn start(&self) -> Result<(), String> {
        let cmd = Command::new("node")
            .arg("dist/index.js")
            .arg("--port")
            .arg(self.port.to_string())
            .arg("--workspace")
            .arg(&self.workspace)
            .current_dir("./remix-runtime")
            .spawn()
            .map_err(|e| format!("Failed to start Remix runtime: {}", e))?;

        *self.process.lock().await = Some(cmd);
        info!("Remix runtime started on port {}", self.port);

        // Health check
        tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;
        Ok(())
    }

    pub async fn stop(&self) -> Result<(), String> {
        if let Some(mut child) = self.process.lock().await.take() {
            child.kill().map_err(|e| format!("Failed to stop Remix: {}", e))?;
            child.wait().map_err(|e| format!("Failed to wait for Remix: {}", e))?;
            info!("Remix runtime stopped");
        }
        Ok(())
    }
}
