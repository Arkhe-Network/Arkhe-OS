//! Sandbox de execução com isolamento real
//!
//! Usa fork() + execvp() + Landlock para isolamento de processos.
//! API Landlock verificada contra landlock 0.4 (Ruleset, PathBeneath, PathFd).

use std::ffi::CString;
use std::os::unix::io::AsRawFd;
use std::os::fd::FromRawFd;
use std::path::Path;
use nix::unistd::{fork, ForkResult, Pid};
use nix::sys::wait::{waitpid, WaitStatus, WaitPidFlag};
use nix::sys::signal::{kill, Signal};
use landlock::{
    Access, AccessFs, PathBeneath, PathFd, RestrictionStatus,
    Ruleset, RulesetAttr, RulesetCreatedAttr, ABI,
};
use crate::error::ExecError;
use crate::gate::ExecutionGate;

/// Resultado de uma execução sandboxed.
#[derive(Debug, Clone)]
pub struct ExecutionResult {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
    pub duration_ms: u64,
}

/// Executor com isolamento real via fork+execvp+Landlock.
pub struct SandboxExecutor {
    gate: ExecutionGate,
}

impl SandboxExecutor {
    pub fn new(gate: ExecutionGate) -> Self {
        Self { gate }
    }

    /// Executa código em subprocesso isolado com Landlock.
    ///
    /// FLUXO DE SEGURANÇA:
    /// 1. Valida interpreter contra whitelist
    /// 2. Escreve código em arquivo temporário no workspace
    /// 3. fork() → filho aplica Landlock → execvp() do interpretador
    /// 4. Pai lê pipes com timeout → kill(SIGKILL) se exceder

    pub fn execute_code(
        &self,
        code: &str,
        interpreter: &str,
    ) -> Result<ExecutionResult, ExecError> {
        // 1. Validar interpreter
        self.gate.validate_binary(interpreter)?;

        // 2. Escrever código em arquivo temporário
        let script_name = format!("script_{}.py", uuid::Uuid::new_v4());
        let script_path = self.gate.workspace.join(&script_name);
        std::fs::write(&script_path, code)?;

        // 3. Construir comando com shlex (previne injection)
        let args = shlex::split(&format!("{} {}", interpreter, script_path.display()))
            .ok_or_else(|| ExecError::Parse("Failed to parse command".into()))?;

        if args.is_empty() {
            return Err(ExecError::Parse("Empty command after shlex split".into()));
        }

        // We use std::process::Command to be able to use pre_exec, then spawn and wait with timeout in a blocking thread, or better yet, since execute_code is a synchronous function, we just block.
        let mut cmd = std::process::Command::new(&args[0]);
        cmd.args(&args[1..]);
        cmd.current_dir(&self.gate.workspace);

        let gate_clone = self.gate.clone();

        unsafe {
            use std::os::unix::process::CommandExt;
            cmd.pre_exec(move || {
                if gate_clone.enable_landlock {
                    if let Err(e) = apply_landlock_sandbox(&gate_clone) {
                        eprintln!("Landlock error: {:?}", e);
                        std::process::exit(1);
                    }
                }
                Ok(())
            });
        }

        let start = std::time::Instant::now();

        // Spawn the child
        use std::process::Stdio;
        use std::io::Read;
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        let mut child = cmd.spawn().map_err(|e| ExecError::Fork(e.to_string()))?;

        let timeout_secs = self.gate.security.timeout_secs;

        // Use a thread to wait with timeout
        let (tx, rx) = std::sync::mpsc::channel();
        let pid = child.id();

        let stdout_opt = child.stdout.take();
        let stderr_opt = child.stderr.take();

        std::thread::spawn(move || {
            let res = child.wait();
            let mut stdout_buf = Vec::new();
            let mut stderr_buf = Vec::new();
            if let Some(mut stdout) = stdout_opt {
                let _ = stdout.read_to_end(&mut stdout_buf);
            }
            if let Some(mut stderr) = stderr_opt {
                let _ = stderr.read_to_end(&mut stderr_buf);
            }
            let _ = tx.send((res, stdout_buf, stderr_buf));
        });

        let result = rx.recv_timeout(std::time::Duration::from_secs(timeout_secs));

        let _ = std::fs::remove_file(&script_path);

        match result {
            Ok((Ok(status), stdout_buf, stderr_buf)) => {
                Ok(ExecutionResult {
                    stdout: String::from_utf8_lossy(&stdout_buf).to_string(),
                    stderr: String::from_utf8_lossy(&stderr_buf).to_string(),
                    exit_code: status.code().unwrap_or(if status.success() { 0 } else { 1 }),
                    duration_ms: start.elapsed().as_millis() as u64,
                })
            }
            Ok((Err(e), stdout_buf, stderr_buf)) => {
                Ok(ExecutionResult {
                    stdout: String::from_utf8_lossy(&stdout_buf).to_string(),
                    stderr: String::from_utf8_lossy(&stderr_buf).to_string(),
                    exit_code: 1,
                    duration_ms: start.elapsed().as_millis() as u64,
                })
            }
            Err(_) => {
                // Timeout
                unsafe {
                    libc::kill(pid as i32, libc::SIGKILL);
                }
                Err(ExecError::Timeout(timeout_secs))
            }
        }
    }


    /// Executa chamada API com validação de gates.

    pub async fn execute_api(
        &self,
        url: &str,
        method: &str,
        body: Option<serde_json::Value>,
    ) -> Result<serde_json::Value, ExecError> {
        // 1. Validar URL contra gates
        let _parsed = self.gate.validate_url(url)?;

        // 2. Construir request com timeout
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(self.gate.security.timeout_secs))
            .build()?;

        let method = reqwest::Method::from_bytes(method.as_bytes())
            .map_err(|e| ExecError::InvalidMethod(e.to_string()))?;

        let mut request = client.request(method, url);
        if let Some(body) = body {
            request = request.json(&body);
        }

        // 3. Executar com limitação de tamanho
        let mut response = request.send().await?;

        let mut bytes = Vec::new();
        while let Some(chunk) = response.chunk().await? {
            bytes.extend_from_slice(&chunk);
            if bytes.len() > self.gate.security.max_response_size {
                return Err(ExecError::Oversized {
                    size: bytes.len(),
                    max: self.gate.security.max_response_size,
                });
            }
        }

        // 4. Parse JSON
        let json: serde_json::Value = serde_json::from_slice(&bytes)
            .map_err(|e| ExecError::Parse(e.to_string()))?;

        Ok(json)
    }

}

/// Aplica sandbox Landlock real usando a API do crate landlock 0.4.
///
/// API verificada: Ruleset::default() → handle_access() → create() →
/// add_rules(PathBeneath::new(PathFd::new(path), access)) → restrict_self()
fn apply_landlock_sandbox(gate: &ExecutionGate) -> Result<RestrictionStatus, ExecError> {
    let abi = ABI::V1;
    let access_all = AccessFs::from_all(abi);
    let access_read = AccessFs::from_read(abi);
    let access_write = AccessFs::from_write(abi);

    let mut ruleset = Ruleset::default()
        .handle_access(access_all)
        .map_err(|e| ExecError::Landlock(format!("handle_access: {:?}", e)))?
        .create()
        .map_err(|e| ExecError::Landlock(format!("create: {:?}", e)))?;

    // Adicionar regras de leitura
    for path in &gate.security.read_paths {
        let fd = PathFd::new(path)
            .map_err(|e| ExecError::Landlock(format!("PathFd {}: {:?}", path.display(), e)))?;
        ruleset = ruleset
            .add_rule(PathBeneath::new(fd, access_read))
            .map_err(|e| ExecError::Landlock(format!("add_rule read: {:?}", e)))?;
    }

    // Adicionar regras de escrita
    for path in &gate.security.write_paths {
        let fd = PathFd::new(path)
            .map_err(|e| ExecError::Landlock(format!("PathFd {}: {:?}", path.display(), e)))?;
        ruleset = ruleset
            .add_rule(PathBeneath::new(fd, access_write))
            .map_err(|e| ExecError::Landlock(format!("add_rule write: {:?}", e)))?;
    }

    // Sempre permitir leitura do workspace
    let workspace_fd = PathFd::new(&gate.workspace)
        .map_err(|e| ExecError::Landlock(format!("PathFd workspace: {:?}", e)))?;
    ruleset = ruleset
        .add_rule(PathBeneath::new(workspace_fd, access_read | access_write))
        .map_err(|e| ExecError::Landlock(format!("add_rule workspace: {:?}", e)))?;

    let status = ruleset
        .restrict_self()
        .map_err(|e| ExecError::Landlock(format!("restrict_self: {:?}", e)))?;

    Ok(status)
}

/// Cria pipe anonimo (read_fd, write_fd).
fn create_pipe() -> Result<(std::fs::File, std::fs::File), std::io::Error> {
    let mut fds = [0i32; 2];
    unsafe {
        if libc::pipe(fds.as_mut_ptr()) != 0 {
            return Err(std::io::Error::last_os_error());
        }
    }
    let read = unsafe { std::fs::File::from_raw_fd(fds[0]) };
    let write = unsafe { std::fs::File::from_raw_fd(fds[1]) };
    Ok((read, write))
}

/// Aguarda child process com timeout usando waitpid(WNOHANG).
fn wait_child_with_timeout(child: Pid, timeout_secs: u64) -> Result<i32, ExecError> {
    let start = std::time::Instant::now();
    let timeout = std::time::Duration::from_secs(timeout_secs);
    let poll_interval = std::time::Duration::from_millis(100);

    loop {
        match waitpid(child, Some(WaitPidFlag::WNOHANG)) {
            Ok(WaitStatus::Exited(_, code)) => return Ok(code),
            Ok(WaitStatus::Signaled(_, sig, _)) => return Ok(128 + sig as i32),
            Ok(WaitStatus::StillAlive) => {
                if start.elapsed() > timeout {
                    let _ = kill(child, Signal::SIGKILL);
                    // Reap zombie
                    let _ = waitpid(child, None);
                    return Ok(137); // SIGKILL exit code
                }
                std::thread::sleep(poll_interval);
            }
            Ok(_) => {
                std::thread::sleep(poll_interval);
            }
            Err(e) => return Err(ExecError::Io(format!("waitpid error: {}", e))),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn test_gate() -> ExecutionGate {
        let mut gate = ExecutionGate::new(
            crate::gate::SecurityGate::default(),
            PathBuf::from("/tmp/safe-core-test"),
        );
        gate.enable_landlock = false; // Desabilitar para testes
        gate
    }

    #[test]
    fn test_validate_binary_allowed() {
        let gate = test_gate();
        assert!(gate.validate_binary("python3").is_ok());
        assert!(gate.validate_binary("/usr/bin/python3").is_ok());
    }

    #[test]
    fn test_validate_binary_denied() {
        let gate = test_gate();
        assert!(gate.validate_binary("rm").is_err());
        assert!(gate.validate_binary("/bin/rm").is_err());
    }

    #[test]
    fn test_validate_url_https() {
        let gate = test_gate();
        assert!(gate.validate_url("https://api.github.com").is_ok());
    }

    #[test]
    fn test_validate_url_http_denied() {
        let gate = test_gate();
        assert!(gate.validate_url("http://insecure.com").is_err());
    }
}
