use anyhow::Result;
use crate::ast::{Node, NodeKind, LiteralKind, Language};
use super::CodeGenerator;

pub struct RustGenerator;

impl RustGenerator {
    pub fn new() -> Self { Self }

    fn generate_node(&self, node: &Node) -> Result<String> {
        match &node.kind {
            NodeKind::Module => {
                let mut code = String::new();
                for child in &node.children {
                    code.push_str(&self.generate_node(child)?);
                    code.push('\n');
                }
                Ok(code)
            }
            NodeKind::FunctionDefinition => {
                let name = node.metadata.get("function_name").and_then(|v| {
                    if let crate::ast::MetadataValue::String(s) = v { Some(s.clone()) } else { None }
                }).unwrap_or_else(|| "fn_name".to_string());
                let params = self.generate_params(node)?;
                let body = self.generate_body(node)?;
                Ok(format!("fn {}({}) {{\n    {}\n}}", name, params, body.trim()))
            }
            NodeKind::VariableDeclaration => {
                let name = node.metadata.get("name").and_then(|v| {
                    if let crate::ast::MetadataValue::String(s) = v { Some(s.clone()) } else { None }
                }).unwrap_or_else(|| "var".to_string());
                let value = self.generate_expression(node)?;
                Ok(format!("let {} = {};", name, value))
            }
            NodeKind::ReturnStatement => {
                if node.children.is_empty() {
                    Ok("return;".to_string())
                } else {
                    let expr = self.generate_node(&node.children[0])?;
                    Ok(format!("return {};", expr))
                }
            }
            NodeKind::Literal(lit) => match lit {
                LiteralKind::String(s) => Ok(format!("{:?}", s)),
                LiteralKind::Integer(i) => Ok(i.to_string()),
                LiteralKind::Float(f) => Ok(f.clone()),
                LiteralKind::Boolean(b) => Ok(b.to_string()),
                _ => Ok("todo".to_string()),
            },
            _ => Ok("/* unsupported node */".to_string()),
        }
    }

    fn generate_params(&self, _node: &Node) -> Result<String> {
        Ok("".to_string())
    }

    fn generate_body(&self, node: &Node) -> Result<String> {
        for child in &node.children {
            if child.kind == NodeKind::Block {
                let mut body = String::new();
                for stmt in &child.children {
                    body.push_str(&self.generate_node(stmt)?);
                    body.push('\n');
                }
                return Ok(body);
            }
        }
        Ok("".to_string())
    }

    fn generate_expression(&self, node: &Node) -> Result<String> {
        if node.children.is_empty() {
            if let Some(name) = node.metadata.get("name").and_then(|v| {
                if let crate::ast::MetadataValue::String(s) = v { Some(s) } else { None }
            }) {
                return Ok(name.clone());
            }
            Ok("todo".to_string())
        } else {
            Ok("todo".to_string())
        }
    }
}

impl CodeGenerator for RustGenerator {
    fn generate(&self, node: &Node) -> Result<String> {
        self.generate_node(node)
    }

    fn language(&self) -> Language {
        Language::Rust
    }
}
