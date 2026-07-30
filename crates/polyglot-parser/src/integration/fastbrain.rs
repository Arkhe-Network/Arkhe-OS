use anyhow::Result;
use crate::ast::Language;
use crate::analysis::vulnerability::VulnerabilityDetector;
use crate::analysis::AnalysisContext;
use crate::parsers::ParserFactory;
use crate::generator::GeneratorFactory;

pub struct FastBrainIntegration {
    parser_factory: ParserFactory,
    detector: VulnerabilityDetector,
    generator: GeneratorFactory,
}

impl FastBrainIntegration {
    pub fn new() -> Self {
        Self {
            parser_factory: ParserFactory::new(),
            detector: VulnerabilityDetector::new(),
            generator: GeneratorFactory::new(),
        }
    }

    pub async fn analyze_code(&self, code: &str, file_path: &str) -> Result<serde_json::Value> {
        let (lang, ast) = self.parser_factory.parse_auto(code).await?;
        let _context = AnalysisContext::new(file_path, code);
        let findings = self.detector.detect(&ast, file_path, code);
        Ok(serde_json::json!({
            "language": format!("{:?}", lang).to_lowercase(),
            "findings": findings,
        }))
    }

    pub async fn generate_fix(&self, code: &str, finding_id: &str, _target_lang: Option<Language>) -> Result<String> {
        Ok(format!("// Fix for vulnerability {}\n{}", finding_id, code))
    }

    pub async fn translate(&self, code: &str, source_lang: Option<Language>, target_lang: Language) -> Result<String> {
        let (_, ast) = match source_lang {
            Some(lang) => {
                let parser = self.parser_factory.get_parser(lang.clone())
                    .ok_or_else(|| anyhow::anyhow!("No parser for {:?}", lang))?;
                let node = parser.parse(code).await?;
                Ok((lang, node))
            }
            None => self.parser_factory.parse_auto(code).await,
        }?;
        self.generator.generate(&ast, target_lang)
    }
}
