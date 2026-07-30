pub mod vulnerability;
pub mod patterns;

use crate::ast::Span;

pub struct AnalysisContext {
    pub file_path: String,
    pub source_code: String,
}

impl AnalysisContext {
    pub fn new(file_path: &str, source_code: &str) -> Self {
        Self {
            file_path: file_path.to_string(),
            source_code: source_code.to_string(),
        }
    }

    pub fn get_snippet(&self, span: &Span) -> String {
        let lines: Vec<&str> = self.source_code.lines().collect();
        if span.start.line > 0 && span.start.line <= lines.len() && span.end.line <= lines.len() {
            let start = span.start.line.saturating_sub(1);
            let end = span.end.line;
            lines[start..end].join("\n")
        } else {
            String::new()
        }
    }
}
