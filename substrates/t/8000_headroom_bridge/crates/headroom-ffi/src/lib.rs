//! crates/headroom-ffi/src/lib.rs
//! Headroom FFI — Integração com Headroom Python via PyO3 + HTTP fallback
//!
//! Selo: CATHEDRAL-ARKHE-8000-HEADROOM-FFI-v1.0.0-2026-06-18
//! Arquiteto: ORCID 0009-0005-2697-4668

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};
use serde::{Serialize, Deserialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use thiserror::Error;

/// ============================================================
/// 1. HEADROOM PYTHON MODULE INTERFACE
/// ============================================================

/// Inicializa o módulo Python Headroom
#[pyfunction]
fn init_headroom_module(py: Python) -> PyResult<&PyModule> {
    let module = PyModule::new(py, "cathedral_headroom")?;

    module.add_function(wrap_pyfunction!(compress_text, module)?)?;
    module.add_function(wrap_pyfunction!(compress_json, module)?)?;
    module.add_function(wrap_pyfunction!(compress_code, module)?)?;
    module.add_function(wrap_pyfunction!(decompress, module)?)?;
    module.add_function(wrap_pyfunction!(get_compression_stats, module)?)?;

    Ok(module)
}

#[pymodule]
fn cathedral_headroom(_py: Python, module: &PyModule) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(init_headroom_module, module)?)?;
    Ok(())
}

/// ============================================================
/// 2. COMPRESSORS HEADROOM REAL
/// ============================================================

/// Compressor Headroom via Python FFI
pub struct HeadroomPythonCompressor {
    /// Instância Python do Headroom
    python: Arc<PythonHeadroomInstance>,
    /// Configuração
    config: HeadroomFfiConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeadroomFfiConfig {
    /// Caminho do virtualenv Python com Headroom
    pub python_path: String,
    /// Módulo Headroom a importar
    pub headroom_module: String,
    /// Timeout de chamada Python (ms)
    pub python_timeout_ms: u64,
    /// Fallback para HTTP se FFI falhar
    pub http_fallback: bool,
    /// URL do Headroom HTTP API
    pub http_api_url: String,
    /// API key para HTTP
    pub http_api_key: Option<String>,
}

impl Default for HeadroomFfiConfig {
    fn default() -> Self {
        Self {
            python_path: "/opt/headroom/venv/bin/python".to_string(),
            headroom_module: "headroom".to_string(),
            python_timeout_ms: 5000,
            http_fallback: true,
            http_api_url: "http://localhost:8787".to_string(),
            http_api_key: None,
        }
    }
}

/// Instância Python gerenciada
pub struct PythonHeadroomInstance {
    /// Gil guard para acesso seguro
    gil: Arc<RwLock<()>>,
}

impl PythonHeadroomInstance {
    pub fn new() -> Result<Self, HeadroomFfiError> {
        // Inicializa Python runtime
        pyo3::prepare_freethreaded_python();

        Ok(Self {
            gil: Arc::new(RwLock::new(())),
        })
    }

    /// Comprime texto via Headroom Python
    pub async fn compress_text(
        &self,
        text: &str,
        max_tokens: Option<usize>,
    ) -> Result<HeadroomCompressionResult, HeadroomFfiError> {
        let _guard = self.gil.read().await;

        Python::with_gil(|py| {
            let headroom = py.import("headroom")?;
            let compressor = headroom.getattr("compress")?;

            let kwargs = PyDict::new(py);
            kwargs.set_item("text", text)?;
            if let Some(max) = max_tokens {
                kwargs.set_item("max_tokens", max)?;
            }

            let result = compressor.call((), Some(kwargs))?;

            let compressed_text: String = result.getattr("text")?.extract()?;
            let compression_ratio: f64 = result.getattr("ratio")?.extract()?;
            let tokens_saved: usize = result.getattr("tokens_saved")?.extract()?;
            let compressor_used: String = result.getattr("compressor")?.extract()?;

            Ok(HeadroomCompressionResult {
                compressed_text,
                compression_ratio,
                tokens_saved,
                compressor_used,
                metadata: None,
            })
        }).map_err(|e: PyErr| HeadroomFfiError::PythonError(e.to_string()))
    }

    /// Comprime JSON via SmartCrusher
    pub async fn compress_json(
        &self,
        json_str: &str,
        max_tokens: Option<usize>,
    ) -> Result<HeadroomCompressionResult, HeadroomFfiError> {
        let _guard = self.gil.read().await;

        Python::with_gil(|py| {
            let headroom = py.import("headroom")?;
            let smart_crusher = headroom.getattr("SmartCrusher")?.call0()?;

            let kwargs = PyDict::new(py);
            kwargs.set_item("json_str", json_str)?;
            if let Some(max) = max_tokens {
                kwargs.set_item("max_tokens", max)?;
            }

            let result = smart_crusher.call_method("compress", (), Some(kwargs))?;

            let compressed_text: String = result.getattr("text")?.extract()?;
            let compression_ratio: f64 = result.getattr("ratio")?.extract()?;
            let tokens_saved: usize = result.getattr("tokens_saved")?.extract()?;

            Ok(HeadroomCompressionResult {
                compressed_text,
                compression_ratio,
                tokens_saved,
                compressor_used: "SmartCrusher".to_string(),
                metadata: None,
            })
        }).map_err(|e: PyErr| HeadroomFfiError::PythonError(e.to_string()))
    }

    /// Comprime código via CodeCompressor
    pub async fn compress_code(
        &self,
        code: &str,
        language: &str,
        max_tokens: Option<usize>,
    ) -> Result<HeadroomCompressionResult, HeadroomFfiError> {
        let _guard = self.gil.read().await;

        Python::with_gil(|py| {
            let headroom = py.import("headroom")?;
            let code_compressor = headroom.getattr("CodeCompressor")?.call1((language,))?;

            let kwargs = PyDict::new(py);
            kwargs.set_item("code", code)?;
            if let Some(max) = max_tokens {
                kwargs.set_item("max_tokens", max)?;
            }

            let result = code_compressor.call_method("compress", (), Some(kwargs))?;

            let compressed_text: String = result.getattr("text")?.extract()?;
            let compression_ratio: f64 = result.getattr("ratio")?.extract()?;
            let tokens_saved: usize = result.getattr("tokens_saved")?.extract()?;
            let ast_preserved: bool = result.getattr("ast_preserved")?.extract()?;

            let mut metadata = HashMap::new();
            metadata.insert("ast_preserved".to_string(), ast_preserved.to_string());

            Ok(HeadroomCompressionResult {
                compressed_text,
                compression_ratio,
                tokens_saved,
                compressor_used: format!("CodeCompressor({})", language),
                metadata: Some(metadata),
            })
        }).map_err(|e: PyErr| HeadroomFfiError::PythonError(e.to_string()))
    }

    /// Decompress via CCR
    pub async fn decompress(
        &self,
        compressed: &str,
        ccr_id: &str,
    ) -> Result<String, HeadroomFfiError> {
        let _guard = self.gil.read().await;

        Python::with_gil(|py| {
            let headroom = py.import("headroom")?;
            let ccr = headroom.getattr("CCR")?.call0()?;

            let result = ccr.call_method1("retrieve", (ccr_id,))?;
            let original: String = result.extract()?;

            Ok(original)
        }).map_err(|e: PyErr| HeadroomFfiError::PythonError(e.to_string()))
    }
}

/// ============================================================
/// 3. HTTP FALLBACK
/// ============================================================

/// Fallback HTTP para quando FFI não está disponível
pub struct HeadroomHttpClient {
    client: reqwest::Client,
    base_url: String,
    api_key: Option<String>,
}

impl HeadroomHttpClient {
    pub fn new(base_url: String, api_key: Option<String>) -> Self {
        Self {
            client: reqwest::Client::new(),
            base_url,
            api_key,
        }
    }

    pub async fn compress(
        &self,
        content: &str,
        content_type: &str,
        max_tokens: Option<usize>,
    ) -> Result<HeadroomCompressionResult, HeadroomFfiError> {
        let mut request = self.client
            .post(format!("{}/api/v1/compress", self.base_url))
            .json(&serde_json::json!({
                "content": content,
                "content_type": content_type,
                "max_tokens": max_tokens,
            }));

        if let Some(ref key) = self.api_key {
            request = request.header("X-API-Key", key);
        }

        let response = request.send().await
            .map_err(|e| HeadroomFfiError::HttpError(e.to_string()))?;

        if !response.status().is_success() {
            return Err(HeadroomFfiError::HttpError(
                format!("HTTP {}", response.status())
            ));
        }

        let result: HeadroomHttpResponse = response.json().await
            .map_err(|e| HeadroomFfiError::HttpError(e.to_string()))?;

        Ok(HeadroomCompressionResult {
            compressed_text: result.compressed_text,
            compression_ratio: result.ratio,
            tokens_saved: result.tokens_saved,
            compressor_used: result.compressor,
            metadata: result.metadata,
        })
    }

    pub async fn retrieve(
        &self,
        ccr_id: &str,
    ) -> Result<String, HeadroomFfiError> {
        let mut request = self.client
            .get(format!("{}/api/v1/retrieve/{}", self.base_url, ccr_id));

        if let Some(ref key) = self.api_key {
            request = request.header("X-API-Key", key);
        }

        let response = request.send().await
            .map_err(|e| HeadroomFfiError::HttpError(e.to_string()))?;

        let result: HeadroomRetrieveResponse = response.json().await
            .map_err(|e| HeadroomFfiError::HttpError(e.to_string()))?;

        Ok(result.original_text)
    }
}

#[derive(Debug, Clone, Deserialize)]
struct HeadroomHttpResponse {
    compressed_text: String,
    ratio: f64,
    tokens_saved: usize,
    compressor: String,
    metadata: Option<HashMap<String, String>>,
}

#[derive(Debug, Clone, Deserialize)]
struct HeadroomRetrieveResponse {
    original_text: String,
}

/// ============================================================
/// 4. UNIFIED COMPRESSOR
/// ============================================================

/// Compressor unificado: tenta FFI, fallback para HTTP
pub struct UnifiedHeadroomCompressor {
    ffi: Option<Arc<PythonHeadroomInstance>>,
    http: Option<HeadroomHttpClient>,
    config: HeadroomFfiConfig,
    metrics: Arc<RwLock<HeadroomCompressorMetrics>>,
}

#[derive(Debug, Clone, Default)]
pub struct HeadroomCompressorMetrics {
    pub ffi_calls: u64,
    pub http_fallbacks: u64,
    pub ffi_errors: u64,
    pub avg_ffi_latency_ms: f64,
    pub avg_http_latency_ms: f64,
}

impl UnifiedHeadroomCompressor {
    pub async fn new(config: HeadroomFfiConfig) -> Result<Self, HeadroomFfiError> {
        // Tenta inicializar FFI
        let ffi = match PythonHeadroomInstance::new() {
            Ok(instance) => {
                tracing::info!("✅ Headroom FFI initialized");
                Some(Arc::new(instance))
            }
            Err(e) => {
                tracing::warn!("⚠️  Headroom FFI failed: {}, using HTTP fallback", e);
                None
            }
        };

        // Inicializa HTTP se necessário
        let http = if ffi.is_none() || config.http_fallback {
            Some(HeadroomHttpClient::new(
                config.http_api_url.clone(),
                config.http_api_key.clone(),
            ))
        } else {
            None
        };

        Ok(Self {
            ffi,
            http,
            config,
            metrics: Arc::new(RwLock::new(HeadroomCompressorMetrics::default())),
        })
    }

    pub async fn compress(
        &self,
        content: &str,
        content_type: &str,
        max_tokens: Option<usize>,
    ) -> Result<HeadroomCompressionResult, HeadroomFfiError> {
        let start = std::time::Instant::now();

        // Tenta FFI primeiro
        if let Some(ref ffi) = self.ffi {
            let result = match content_type {
                "json" => ffi.compress_json(content, max_tokens).await,
                "code" => ffi.compress_code(content, "auto", max_tokens).await,
                _ => ffi.compress_text(content, max_tokens).await,
            };

            match result {
                Ok(r) => {
                    let mut metrics = self.metrics.write().await;
                    metrics.ffi_calls += 1;
                    metrics.avg_ffi_latency_ms =
                        (metrics.avg_ffi_latency_ms * (metrics.ffi_calls - 1) as f64 + start.elapsed().as_millis() as f64)
                        / metrics.ffi_calls as f64;
                    return Ok(r);
                }
                Err(e) => {
                    let mut metrics = self.metrics.write().await;
                    metrics.ffi_errors += 1;
                    tracing::warn!("FFI error: {}, falling back to HTTP", e);
                }
            }
        }

        // Fallback HTTP
        if let Some(ref http) = self.http {
            let result = http.compress(content, content_type, max_tokens).await;

            let mut metrics = self.metrics.write().await;
            metrics.http_fallbacks += 1;
            metrics.avg_http_latency_ms =
                (metrics.avg_http_latency_ms * (metrics.http_fallbacks - 1) as f64 + start.elapsed().as_millis() as f64)
                / metrics.http_fallbacks as f64;

            return result;
        }

        Err(HeadroomFfiError::NoBackendAvailable)
    }

    pub async fn get_metrics(&self) -> HeadroomCompressorMetrics {
        self.metrics.read().await.clone()
    }
}

/// ============================================================
/// 5. TIPOS E ERROS
/// ============================================================

#[derive(Debug, Clone)]
pub struct HeadroomCompressionResult {
    pub compressed_text: String,
    pub compression_ratio: f64,
    pub tokens_saved: usize,
    pub compressor_used: String,
    pub metadata: Option<HashMap<String, String>>,
}

use std::collections::HashMap;

#[derive(Debug, Error)]
pub enum HeadroomFfiError {
    #[error("Python error: {0}")]
    PythonError(String),
    #[error("HTTP error: {0}")]
    HttpError(String),
    #[error("No backend available (FFI and HTTP both failed)")]
    NoBackendAvailable,
    #[error("Compression failed: {0}")]
    CompressionFailed(String),
    #[error("Decompression failed: {0}")]
    DecompressionFailed(String),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_http_fallback_compress() {
        // Testa com HTTP mock
        let config = HeadroomFfiConfig {
            python_path: "/nonexistent".to_string(),
            http_fallback: true,
            http_api_url: "http://localhost:9999".to_string(),
            ..Default::default()
        };

        let compressor = UnifiedHeadroomCompressor::new(config).await.unwrap();
        // Sem mock server, deve falhar com NoBackendAvailable
        let result = compressor.compress("test", "text", None).await;
        assert!(result.is_err());
    }

    #[test]
    fn test_compression_result() {
        let result = HeadroomCompressionResult {
            compressed_text: "compressed".to_string(),
            compression_ratio: 0.5,
            tokens_saved: 100,
            compressor_used: "SmartCrusher".to_string(),
            metadata: None,
        };

        assert_eq!(result.compression_ratio, 0.5);
        assert_eq!(result.tokens_saved, 100);
    }
}
