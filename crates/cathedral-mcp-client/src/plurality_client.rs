use crate::types::*;
use crate::auth::{PluralityAuth, OAuthToken};
use crate::jwks::JwksValidator;
use reqwest::{Client, Method, header::{AUTHORIZATION, CONTENT_TYPE}};
use serde_json::{json, Value};
use std::sync::Arc;
use tokio::sync::{Mutex, RwLock};
use tracing::{info, debug, error, warn, instrument, span, Span, Level};
use std::collections::HashMap;
use chrono::Utc;
use crate::McpError;

struct ClientState {
    auth: PluralityAuth,
    token: Option<OAuthToken>,
    last_refresh_attempt: chrono::DateTime<chrono::Utc>,
}

pub struct PluralityMcpClient {
    http_client: Client,
    endpoint: String,
    state: Arc<RwLock<ClientState>>,
    jwks_validator: Option<Arc<JwksValidator>>,
    content_cache: Arc<Mutex<HashMap<String, (String, chrono::DateTime<chrono::Utc>)>>>,
}

impl PluralityMcpClient {
    pub async fn new(endpoint: &str, auth: PluralityAuth) -> Result<Self, McpError> {
        let http_client = Client::builder()
            .timeout(std::time::Duration::from_secs(30))
            .build()
            .map_err(|e| McpError::Transport(e.to_string()))?;

        let state = ClientState {
            auth: auth.clone(),
            token: None,
            last_refresh_attempt: chrono::Utc::now() - chrono::Duration::days(1),
        };

        let mut client = Self {
            http_client,
            endpoint: endpoint.to_string(),
            state: Arc::new(RwLock::new(state)),
            jwks_validator: Some(Arc::new(JwksValidator::new(
                "https://app.plurality.network/.well-known/jwks.json",
                300,
            ))),
            content_cache: Arc::new(Mutex::new(HashMap::new())),
        };

        {
            let mut state = client.state.write().await;
            if let PluralityAuth::OAuth2 { token_cache, .. } = &mut state.auth {
                if let Some(token) = token_cache.take() {
                    state.token = Some(token);
                }
            }
        }

        Ok(client)
    }

    async fn get_auth_header(&self) -> Result<String, McpError> {
        let span = span!(Level::DEBUG, "get_auth_header");
        let _enter = span.enter();

        let mut token_str = String::new();
        let mut needs_refresh = false;
        let mut refresh_token = None;
        let mut config_clone = None;

        {
            let state = self.state.read().await;
            match &state.auth {
                PluralityAuth::Pat { token } => {
                    token_str = token.clone();
                }
                PluralityAuth::OAuth2 { config, .. } => {
                    if let Some(token) = &state.token {
                        if !token.is_expired() {
                            token_str = token.access_token.clone();
                        } else {
                            needs_refresh = true;
                            refresh_token = token.refresh_token.clone();
                            config_clone = Some(config.clone());
                        }
                    } else {
                        needs_refresh = true;
                        config_clone = Some(config.clone());
                    }
                }
            }
        }

        if !token_str.is_empty() {
             return Ok(format!("Bearer {}", token_str));
        }

        if needs_refresh {
             if let (Some(refresh), Some(config)) = (refresh_token, config_clone) {
                  let mut state = self.state.write().await;
                  let now = chrono::Utc::now();
                  let last_attempt = state.last_refresh_attempt;
                  if (now - last_attempt).num_seconds() < 5 {
                        return Err(McpError::Auth("Refresh already in progress, retry later".to_string()));
                  }
                  state.last_refresh_attempt = now;
                  drop(state);

                  let flow = crate::auth::OAuthFlow::new(config);
                  let new_token = flow.refresh_token(&refresh).await?;

                  let mut state = self.state.write().await;
                  let ret_token = new_token.access_token.clone();
                  state.token = Some(new_token);
                  return Ok(format!("Bearer {}", ret_token));

             } else {
                 return Err(McpError::Auth("No refresh token available".to_string()));
             }
        }

        Err(McpError::Auth("No auth method available".to_string()))
    }

    #[instrument(skip(self, args), fields(tool_name = %tool_name))]
    async fn call_tool(&self, tool_name: &str, args: Value) -> Result<Value, McpError> {
        let auth_header = self.get_auth_header().await?;

        let payload = json!({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            },
            "id": 1
        });

        let start = std::time::Instant::now();

        let response = self.http_client
            .request(Method::POST, &self.endpoint)
            .header(AUTHORIZATION, &auth_header)
            .header(CONTENT_TYPE, "application/json")
            .json(&payload)
            .send()
            .await
            .map_err(|e| McpError::Transport(e.to_string()))?;

        let elapsed = start.elapsed();
        tracing::info!(duration_ms = elapsed.as_millis(), "MCP call completed");

        if !response.status().is_success() {
            let status = response.status();
            let headers = response.headers().clone();
            let err_text = response.text().await.unwrap_or_default();

            if status == 429 {
                let retry_after = headers
                    .get("retry-after")
                    .and_then(|v| v.to_str().ok())
                    .and_then(|s| s.parse::<u64>().ok())
                    .map(|secs| chrono::Duration::seconds(secs as i64));
                return Err(McpError::RateLimited { retry_after });
            } else if status == 403 {
                return Err(McpError::ConsentRevoked { bucket: "unknown".to_string() });
            } else if status == 404 {
                return Err(McpError::BucketNotFound("unknown".to_string()));
            } else {
                return Err(McpError::Api(format!("HTTP {}: {}", status, err_text)));
            }
        }

        let body: Value = response.json().await
            .map_err(|e| McpError::Api(e.to_string()))?;

        if let Some(error) = body.get("error") {
            let code = error.get("code").and_then(|v| v.as_i64()).unwrap_or(-1);
            let msg = error.get("message").and_then(|v| v.as_str()).unwrap_or("Unknown error");

            match code {
                404 => return Err(McpError::BucketNotFound(msg.to_string())),
                403 => return Err(McpError::ConsentRevoked { bucket: "unknown".to_string() }),
                429 => return Err(McpError::RateLimited { retry_after: None }),
                _ => return Err(McpError::Api(format!("MCP error {}: {}", code, msg))),
            }
        }

        let result = body.get("result")
            .ok_or_else(|| McpError::InvalidResponse)?;

        Ok(result.clone())
    }

    pub async fn get_user_memory_buckets(&self) -> Result<Vec<MemoryBucket>, McpError> {
        let result = self.call_tool("get_user_memory_buckets", json!({})).await?;
        let buckets: Vec<MemoryBucket> = serde_json::from_value(result)
            .map_err(|e| McpError::Serialization(e))?;
        Ok(buckets)
    }

    pub async fn list_items_in_memory_bucket(&self, bucket_id: &str) -> Result<Vec<Value>, McpError> {
        let result = self.call_tool("list_items_in_memory_bucket", json!({"bucket_id": bucket_id})).await?;
        let items: Vec<Value> = serde_json::from_value(result)
            .map_err(|e| McpError::Serialization(e))?;
        Ok(items)
    }

    pub async fn search_memory(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>, McpError> {
        let result = self.call_tool("search_memory", json!({"query": query, "limit": limit})).await?;
        let results: Vec<SearchResult> = serde_json::from_value(result)
            .map_err(|e| McpError::Serialization(e))?;
        Ok(results)
    }

    pub async fn read_context(&self, item_id: &str, page: usize) -> Result<ContextItem, McpError> {
        let result = self.call_tool("read_context", json!({"item_id": item_id, "page": page})).await?;
        let item: ContextItem = serde_json::from_value(result)
            .map_err(|e| McpError::Serialization(e))?;
        Ok(item)
    }

    pub async fn save_memory(&self, bucket_id: &str, content: &str, title: Option<&str>) -> Result<(), McpError> {
        let mut args = json!({
            "bucket_id": bucket_id,
            "content": content,
        });
        if let Some(title) = title {
            args["title"] = json!(title);
        }
        self.call_tool("save_memory", args).await?;

        self.invalidate_cache_for_bucket(bucket_id).await;

        Ok(())
    }

    pub async fn save_conversation(&self, bucket_id: &str, messages: Vec<Message>, summary: Option<&str>) -> Result<(), McpError> {
        let args = json!({
            "bucket_id": bucket_id,
            "messages": messages,
            "summary": summary,
        });
        self.call_tool("save_conversation", args).await?;
        self.invalidate_cache_for_bucket(bucket_id).await;
        Ok(())
    }

    pub async fn create_memory_bucket(&self, name: &str, description: Option<&str>) -> Result<String, McpError> {
        let mut args = json!({"name": name});
        if let Some(desc) = description {
            args["description"] = json!(desc);
        }
        let result = self.call_tool("create_memory_bucket", args).await?;
        let bucket_id = result.get("id").and_then(|v| v.as_str())
            .ok_or_else(|| McpError::InvalidResponse)?;
        Ok(bucket_id.to_string())
    }

    async fn invalidate_cache_for_bucket(&self, bucket_id: &str) {
        let mut cache = self.content_cache.lock().await;
        cache.retain(|_, (_, _)| false);
        debug!("Invalidated cache for bucket: {}", bucket_id);
    }

    pub async fn check_cache_invalidation(&self, item_id: &str, current_hash: &str) -> bool {
        let cache = self.content_cache.lock().await;
        if let Some((stored_hash, _)) = cache.get(item_id) {
            if stored_hash != current_hash {
                return true;
            }
        }
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_client_creation() {
        let auth = PluralityAuth::Pat { token: "test_pat".to_string() };
        let client = PluralityMcpClient::new("https://app.plurality.network/mcp", auth).await;
        assert!(client.is_ok());
    }
}
