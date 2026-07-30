use axum::{
    extract::Request,
    http::HeaderMap,
    middleware::Next,
    response::{Response, IntoResponse, Json},
};
use serde_json::json;
use cathedral_identity::{Did, verify_signature};

pub async fn did_auth_middleware(
    headers: HeaderMap,
    mut req: Request,
    next: Next,
) -> Result<Response, Response> {
    let auth_header = headers
        .get("Authorization")
        .and_then(|v| v.to_str().ok())
        .ok_or_else(|| {
            (
                axum::http::StatusCode::UNAUTHORIZED,
                Json(json!({ "error": "Missing Authorization header" })),
            ).into_response()
        })?;

    let parts: Vec<&str> = auth_header.split_whitespace().collect();
    if parts.len() != 2 || parts[0] != "Bearer" {
        return Err((
            axum::http::StatusCode::UNAUTHORIZED,
            Json(json!({ "error": "Invalid Authorization format. Use: Bearer <did>:<signature>" })),
        ).into_response());
    }

    let token = parts[1];
    let (did_str, sig_hex) = token.split_once(':').ok_or_else(|| {
        (
            axum::http::StatusCode::UNAUTHORIZED,
            Json(json!({ "error": "Invalid token format. Use: <did>:<signature>" })),
        ).into_response()
    })?;

    let did = Did::parse(did_str).map_err(|_| {
        (
            axum::http::StatusCode::UNAUTHORIZED,
            Json(json!({ "error": "Invalid DID format" })),
        ).into_response()
    })?;

    let sig = hex::decode(sig_hex).map_err(|_| {
        (
            axum::http::StatusCode::UNAUTHORIZED,
            Json(json!({ "error": "Invalid signature format (expected hex)" })),
        ).into_response()
    })?;

    let message_str = req.uri().to_string();
    let message = message_str.as_bytes();
    if !verify_signature(&did, &sig, message) {
        return Err((
            axum::http::StatusCode::UNAUTHORIZED,
            Json(json!({ "error": "Invalid signature" })),
        ).into_response());
    }

    req.extensions_mut().insert(did);
    Ok(next.run(req).await)
}
