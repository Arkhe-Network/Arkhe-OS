
pub struct ReflectServer {}
pub struct PatternResult { pub slug: String, pub lesson: String }
impl ReflectServer {
    pub fn new() -> Self { Self {} }
    pub fn process_log(&mut self, _log: &str, _task: &str) -> Vec<PatternResult> { vec![] }
}
