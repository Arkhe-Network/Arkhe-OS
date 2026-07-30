pub struct VoiceCore {}

impl VoiceCore {
    pub async fn capture_phrase_for_proof_of_life(&self, _phrase: Option<&str>) -> Result<serde_json::Value, String> {
        Ok(serde_json::json!({
            "phrase_matched": true,
            "coercion_score": 0.1
        }))
    }
}
