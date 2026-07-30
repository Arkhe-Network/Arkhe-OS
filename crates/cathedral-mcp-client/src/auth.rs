use oauth2::{
    basic::BasicClient,
    AuthUrl, ClientId, ClientSecret, RedirectUrl, TokenUrl,
    AuthorizationCode, CsrfToken, PkceCodeChallenge, PkceCodeVerifier, Scope, TokenResponse
};
use serde::{Deserialize, Serialize};
use tracing::{debug, warn};
use backoff::future::retry;
use backoff::ExponentialBackoff;
use std::time::Duration;
use crate::McpError;

#[derive(Debug, Clone)]
pub enum PluralityAuth {
    Pat { token: String },
    OAuth2 {
        config: OAuthConfig,
        token_cache: Option<OAuthToken>,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OAuthConfig {
    pub client_id: String,
    pub client_secret: String,
    pub auth_url: String,
    pub token_url: String,
    pub register_url: String,
    pub redirect_uri: String,
    pub scopes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PatToken {
    pub token: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OAuthToken {
    pub access_token: String,
    pub refresh_token: Option<String>,
    pub expires_in: u64,
    pub expires_at: chrono::DateTime<chrono::Utc>,
}

impl OAuthToken {
    pub fn is_expired(&self) -> bool {
        chrono::Utc::now() >= self.expires_at
    }

    pub fn remaining_seconds(&self) -> i64 {
        (self.expires_at - chrono::Utc::now()).num_seconds()
    }
}

pub struct OAuthFlow {
    config: OAuthConfig,
    client: BasicClient,
    pkce_verifier: Option<PkceCodeVerifier>,
    pkce_challenge: Option<PkceCodeChallenge>,
}

impl OAuthFlow {
    pub fn new(config: OAuthConfig) -> Self {
        let client = BasicClient::new(
            ClientId::new(config.client_id.clone()),
            Some(ClientSecret::new(config.client_secret.clone())),
            AuthUrl::new(config.auth_url.clone()).unwrap(),
            Some(TokenUrl::new(config.token_url.clone()).unwrap()),
        )
        .set_redirect_uri(RedirectUrl::new(config.redirect_uri.clone()).unwrap());

        Self {
            config,
            client,
            pkce_verifier: None,
            pkce_challenge: None,
        }
    }

    pub fn generate_auth_url(&mut self) -> (String, CsrfToken) {
        let (pkce_challenge, pkce_verifier) = PkceCodeChallenge::new_random_sha256();
        self.pkce_verifier = Some(pkce_verifier);
        self.pkce_challenge = Some(pkce_challenge.clone());

        let (url, csrf_token) = self.client
            .authorize_url(CsrfToken::new_random)
            .add_scope(Scope::new("openid".to_string()))
            .add_scope(Scope::new("profile".to_string()))
            .add_scope(Scope::new("memory:read".to_string()))
            .add_scope(Scope::new("memory:write".to_string()))
            .set_pkce_challenge(pkce_challenge)
            .url();

        (url.to_string(), csrf_token)
    }

    pub async fn exchange_code(
        &mut self,
        code: AuthorizationCode,
        _csrf_token: CsrfToken,
    ) -> Result<OAuthToken, McpError> {
        let verifier = self.pkce_verifier
            .take()
            .ok_or_else(|| McpError::Auth("PKCE verifier not set".to_string()))?;

        let token_response = self.client
            .exchange_code(code)
            .set_pkce_verifier(verifier)
            .request_async(&oauth2::reqwest::async_http_client)
            .await
            .map_err(|e| McpError::Auth(e.to_string()))?;

        let expires_at = chrono::Utc::now() + chrono::Duration::seconds(token_response.expires_in().unwrap_or(std::time::Duration::from_secs(3600)).as_secs() as i64);

        Ok(OAuthToken {
            access_token: token_response.access_token().secret().clone(),
            refresh_token: token_response.refresh_token().map(|t| t.secret().clone()),
            expires_in: token_response.expires_in().unwrap_or(std::time::Duration::from_secs(3600)).as_secs(),
            expires_at,
        })
    }

    pub async fn refresh_token(&self, refresh_token: &str) -> Result<OAuthToken, McpError> {
        let operation = || async {
            debug!("Refreshing OAuth token...");
            let token_response = self.client
                .exchange_refresh_token(&oauth2::RefreshToken::new(refresh_token.to_string()))
                .request_async(&oauth2::reqwest::async_http_client)
                .await
                .map_err(|e| {
                    warn!("Refresh token failed: {}", e);
                    backoff::Error::Transient { err: McpError::Auth(e.to_string()), retry_after: None }
                })?;

            let expires_at = chrono::Utc::now() + chrono::Duration::seconds(token_response.expires_in().unwrap_or(std::time::Duration::from_secs(3600)).as_secs() as i64);

            Ok(OAuthToken {
                access_token: token_response.access_token().secret().clone(),
                refresh_token: token_response.refresh_token().map(|t| t.secret().clone()),
                expires_in: token_response.expires_in().unwrap_or(std::time::Duration::from_secs(3600)).as_secs(),
                expires_at,
            })
        };

        let backoff_config = ExponentialBackoff {
            initial_interval: Duration::from_millis(500),
            max_interval: Duration::from_secs(10),
            multiplier: 2.0,
            max_elapsed_time: Some(Duration::from_secs(30)),
            ..ExponentialBackoff::default()
        };

        retry(backoff_config, operation)
            .await
            .map_err(|e: backoff::Error<McpError>| McpError::Auth(format!("Refresh token failed after retries: {}", e)))
    }
}
