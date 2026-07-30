use anyhow::Result;
use crate::ast::{Node, Language};
use super::CodeGenerator;

pub struct GoGenerator;
impl GoGenerator { pub fn new() -> Self { Self } }
impl CodeGenerator for GoGenerator {
    fn generate(&self, _node: &Node) -> Result<String> { Ok("// stub".to_string()) }
    fn language(&self) -> Language { Language::Go }
}
