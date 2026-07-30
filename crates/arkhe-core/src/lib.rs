pub mod string_safe;

#[derive(Debug)]
pub enum ArkheError {
    Internal(String),
}
