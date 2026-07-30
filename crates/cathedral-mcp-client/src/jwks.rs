use jsonwebtoken::{decode, DecodingKey, Validation, Algorithm, TokenData};
use serde::{Deserialize, Serialize};
use reqwest::Client;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;
use tracing::{debug, warn};
use chrono::{Utc, Duration};
use crate::McpError;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct JwksKey {
    kid: String,
    kty: String,
    alg: String,
    n: String,
    e: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct JwksResponse {
    keys: Vec<JwksKey>,
}

pub struct JwksValidator {
    client: Client,
    jwks_url: String,
    cache: Arc<Mutex<HashMap<String, (DecodingKey, chrono::DateTime<chrono::Utc>)>>>,
    cache_ttl_seconds: u64,
}

impl JwksValidator {
    pub fn new(jwks_url: &str, cache_ttl_seconds: u64) -> Self {
        Self {
            client: Client::new(),
            jwks_url: jwks_url.to_string(),
            cache: Arc::new(Mutex::new(HashMap::new())),
            cache_ttl_seconds,
        }
    }

    async fn get_decoding_key(&self, kid: &str) -> Result<DecodingKey, McpError> {
        let mut cache = self.cache.lock().await;

        if let Some((key, expires_at)) = cache.get(kid) {
            if Utc::now() < *expires_at {
                debug!("JWKS cache hit for kid {}", kid);
                return Ok(key.clone());
            }
        }

        debug!("Fetching JWKS from {}", self.jwks_url);
        let resp = self.client.get(&self.jwks_url)
            .send()
            .await
            .map_err(|e| McpError::Transport(e.to_string()))?;

        if !resp.status().is_success() {
            return Err(McpError::Api(format!("JWKS fetch failed: {}", resp.status())));
        }

        let jwks: JwksResponse = resp.json()
            .await
            .map_err(|e| McpError::Api(e.to_string()))?;

        let now = Utc::now();
        let expires_at = now + Duration::seconds(self.cache_ttl_seconds as i64);

        for key in jwks.keys {
            if key.kty == "RSA" {
                let decoding_key = DecodingKey::from_rsa_components(&key.n, &key.e)
                    .map_err(|e| McpError::JwtError(e.to_string()))?;
                cache.insert(key.kid, (decoding_key, expires_at));
            }
        }

        if let Some((key, _)) = cache.get(kid) {
            Ok(key.clone())
        } else {
            Err(McpError::JwtError(format!("Key with kid '{}' not found in JWKS", kid)))
        }
    }

    pub async fn validate(&self, token: &str) -> Result<TokenData<serde_json::Value>, McpError> {
        let header = jsonwebtoken::decode_header(token)
            .map_err(|e| McpError::JwtError(e.to_string()))?;

        let kid = header.kid
            .ok_or_else(|| McpError::JwtError("Missing kid in JWT header".to_string()))?;

        let decoding_key = self.get_decoding_key(&kid).await?;

        let mut validation = Validation::new(Algorithm::RS256);
        validation.validate_exp = true;
        validation.validate_nbf = true;

        let token_data = decode::<serde_json::Value>(token, &decoding_key, &validation)
            .map_err(|e| McpError::JwtError(e.to_string()))?;

        Ok(token_data)
    }
}
