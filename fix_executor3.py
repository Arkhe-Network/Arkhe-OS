import re

with open('safe-core/crates/action-executor/src/sandbox.rs', 'r') as f:
    text = f.read()

# Fix execute_api to check content length streamingly
new_execute_api = """
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
"""

text = re.sub(r'pub async fn execute_api\(.*?\) -> Result<serde_json::Value, ExecError> \{.*?Ok\(json\)\n    \}', new_execute_api, text, flags=re.DOTALL)

with open('safe-core/crates/action-executor/src/sandbox.rs', 'w') as f:
    f.write(text)
