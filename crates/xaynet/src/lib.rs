
pub struct Coordinator {}
impl Coordinator {
    pub fn new() -> Self { Self {} }
    pub fn add_participant(&mut self, _p: Participant) {}
    pub fn aggregate(&self) -> Result<Model, ()> { Ok(Model {}) }
}
pub struct Participant {}
impl Participant {
    pub fn new(_m: Model) -> Self { Self {} }
}
pub struct Model {}
