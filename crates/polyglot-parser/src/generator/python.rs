use anyhow::Result;
use crate::ast::{Node, Language};
use super::CodeGenerator;

pub struct PythonGenerator;
impl PythonGenerator { pub fn new() -> Self { Self } }
impl CodeGenerator for PythonGenerator {
    fn generate(&self, _node: &Node) -> Result<String> { Ok("# stub".to_string()) }
    fn language(&self) -> Language { Language::Python }
}
