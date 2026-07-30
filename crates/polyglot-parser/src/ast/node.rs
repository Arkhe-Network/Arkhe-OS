use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub kind: NodeKind,
    pub span: Span,
    pub children: Vec<Node>,
    pub metadata: HashMap<String, MetadataValue>,
    pub language: Language,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum NodeKind {
    Module,
    FunctionDefinition,
    FunctionDeclaration,
    ClassDeclaration,
    StructDeclaration,
    InterfaceDeclaration,
    EnumDeclaration,
    VariableDeclaration,
    ConstantDeclaration,
    ImportDeclaration,
    ExportDeclaration,

    Block,
    IfStatement,
    ForStatement,
    WhileStatement,
    DoWhileStatement,
    SwitchStatement,
    CaseStatement,
    DefaultCase,
    ReturnStatement,
    BreakStatement,
    ContinueStatement,
    ExpressionStatement,
    EmptyStatement,

    Identifier,
    Literal(LiteralKind),
    BinaryExpression,
    UnaryExpression,
    AssignmentExpression,
    CallExpression,
    MethodCall,
    MemberAccess,
    IndexAccess,
    NewExpression,
    ArrowFunction,
    TemplateLiteral,
    ConditionalExpression,
    LogicalExpression,
    SpreadElement,

    Pattern,
    ObjectPattern,
    ArrayPattern,

    TypeAnnotation,
    TypeReference,
    GenericType,
    UnionType,
    IntersectionType,

    Comment,
    Documentation,
    VulnerabilityMarker,
    SecurityAnnotation,
    EvolutionProposal,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum LiteralKind {
    String(String),
    Integer(i64),
    Float(String),
    Boolean(bool),
    Null,
    Undefined,
    RegExp(String),
    Template(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MetadataValue {
    String(String),
    Integer(i64),
    Float(f64),
    Boolean(bool),
    Array(Vec<MetadataValue>),
    Object(HashMap<String, MetadataValue>),
    Null,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Span {
    pub start: Position,
    pub end: Position,
}

impl Span {
    pub fn new(start: Position, end: Position) -> Self {
        Self { start, end }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Position {
    pub line: usize,
    pub column: usize,
    pub offset: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Language {
    Rust,
    Python,
    Go,
    TypeScript,
    JavaScript,
    Lua,
    Solidity,
    Move,
    AssemblyScript,
    Unknown,
}

impl Language {
    pub fn from_extension(ext: &str) -> Self {
        match ext {
            "rs" => Language::Rust,
            "py" => Language::Python,
            "go" => Language::Go,
            "ts" => Language::TypeScript,
            "js" => Language::JavaScript,
            "lua" => Language::Lua,
            "sol" => Language::Solidity,
            "move" => Language::Move,
            "as" => Language::AssemblyScript,
            _ => Language::Unknown,
        }
    }

    pub fn extension(&self) -> &'static str {
        match self {
            Language::Rust => "rs",
            Language::Python => "py",
            Language::Go => "go",
            Language::TypeScript => "ts",
            Language::JavaScript => "js",
            Language::Lua => "lua",
            Language::Solidity => "sol",
            Language::Move => "move",
            Language::AssemblyScript => "as",
            Language::Unknown => "txt",
        }
    }

    pub fn is_supported(&self) -> bool {
        !matches!(self, Language::Unknown)
    }
}
