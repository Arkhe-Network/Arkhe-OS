#[derive(Debug, Clone)]
pub enum ModelTier {
    Pro,
    Plus,
    Standard,
    Lite,
}

impl std::fmt::Display for ModelTier {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ModelTier::Pro => write!(f, "Pro"),
            ModelTier::Plus => write!(f, "Plus"),
            ModelTier::Standard => write!(f, "Standard"),
            ModelTier::Lite => write!(f, "Lite"),
        }
    }
}

pub struct CathedralCore {}
impl CathedralCore {
    pub async fn new() -> Self {
        Self {}
    }
    pub fn for_tier(&self, _tier: ModelTier) -> &Self {
        self
    }
    pub async fn generate_with_thinking(
        &self,
        prompt: &str,
    ) -> Result<(String, Option<String>), String> {
        let is_l0 = prompt.contains("Verification level: None");
        let thinking = if is_l0 {
            None
        } else {
            Some("Thinking...".to_string())
        };
        let mut text = prompt.to_string();
        if prompt.contains("Qual é o meu nome?") {
            text = "João".to_string();
        }
        Ok((text, thinking))
    }
}
