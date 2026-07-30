import re

with open('safe-core/crates/action-executor/src/sandbox.rs', 'r') as f:
    text = f.read()

# Let's replace the whole SandboxExecutor::execute_code method with tokio::process::Command
new_execute_code = """
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
"""

text = re.sub(r'pub fn execute_code\(.*?\) -> Result<ExecutionResult, ExecError> \{.*?\n    \}', new_execute_code, text, flags=re.DOTALL)

with open('safe-core/crates/action-executor/src/sandbox.rs', 'w') as f:
    f.write(text)
