use anyhow::Result;
use crate::ast::Language;
use crate::analysis::vulnerability::{VulnerabilityDetector, Finding};
use crate::analysis::AnalysisContext;
use crate::parsers::ParserFactory;

pub struct OpenAntIntegration {
    parser_factory: ParserFactory,
    detector: VulnerabilityDetector,
}

impl OpenAntIntegration {
    pub fn new() -> Self {
        Self {
            parser_factory: ParserFactory::new(),
            detector: VulnerabilityDetector::new(),
        }
    }

    pub async fn scan_directory(&self, dir_path: &str) -> Result<Vec<Finding>> {
        let mut all_findings = Vec::new();
        let mut entries = tokio::fs::read_dir(dir_path).await?;

        while let Some(entry) = entries.next_entry().await? {
            let path = entry.path();
            if path.is_file() {
                if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                    let lang = Language::from_extension(ext);
                    if lang.is_supported() {
                        let code = tokio::fs::read_to_string(&path).await?;
                        let findings = self.scan_file(&code, path.to_str().unwrap_or("")).await?;
                        all_findings.extend(findings);
                    }
                }
            } else if path.is_dir() {
                let sub_findings = Box::pin(self.scan_directory(path.to_str().unwrap_or(""))).await?;
                all_findings.extend(sub_findings);
            }
        }

        Ok(all_findings)
    }

    pub async fn scan_file(&self, code: &str, file_path: &str) -> Result<Vec<Finding>> {
        let (_lang, ast) = self.parser_factory.parse_auto(code).await?;
        let _context = AnalysisContext::new(file_path, code);
        let findings = self.detector.detect(&ast, file_path, code);
        Ok(findings)
    }

    pub async fn scan_code(&self, code: &str, language: Option<Language>) -> Result<Vec<Finding>> {
        let ast = if let Some(lang) = language {
            let parser = self.parser_factory.get_parser(lang.clone())
                .ok_or_else(|| anyhow::anyhow!("No parser for {:?}", lang))?;
            parser.parse(code).await?
        } else {
            let (_, ast) = self.parser_factory.parse_auto(code).await?;
            ast
        };

        let _context = AnalysisContext::new("memory", code);
        let findings = self.detector.detect(&ast, "memory", code);
        Ok(findings)
    }
}
