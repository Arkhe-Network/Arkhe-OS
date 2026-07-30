import os
import subprocess

def create_dummy_crate(name):
    os.makedirs(f"crates/{name}/src", exist_ok=True)
    with open(f"crates/{name}/Cargo.toml", "w") as f:
        f.write(f'''[package]
name = "{name}"
version = "0.1.0"
edition = "2021"

[dependencies]
''')
    with open(f"crates/{name}/src/lib.rs", "w") as f:
        if name == "xaynet":
            f.write('''
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
''')
        elif name == "sealy":
            f.write('''
pub struct BFVContext {}
impl BFVContext {
    pub fn new(_a: u32, _b: u32) -> Self { Self {} }
}
pub struct BFVEncoder {}
impl BFVEncoder {
    pub fn new(_ctx: &BFVContext) -> Self { Self {} }
}
pub struct BFVEvaluator {}
impl BFVEvaluator {
    pub fn new(_ctx: &BFVContext) -> Self { Self {} }
    pub fn add(&self, a: &[u8], _b: &[u8]) -> Vec<u8> { a.to_vec() }
}
pub struct BFVKeyGenerator {}
impl BFVKeyGenerator {
    pub fn new(_ctx: &BFVContext) -> Self { Self {} }
}
''')
        elif name == "arya-stark":
            f.write('''
pub struct Gradient {}
pub struct GradientProof {}
pub fn prove_gradient(_g: &Gradient) -> Result<GradientProof, ()> { Ok(GradientProof {}) }
pub fn verify_gradient(_p: &GradientProof) -> Result<bool, ()> { Ok(true) }
''')
        elif name == "reflect-mcp":
            f.write('''
pub struct ReflectServer {}
pub struct PatternResult { pub slug: String, pub lesson: String }
impl ReflectServer {
    pub fn new() -> Self { Self {} }
    pub fn process_log(&mut self, _log: &str, _task: &str) -> Vec<PatternResult> { vec![] }
}
''')
        elif name == "optimizer":
            f.write('''
use std::collections::HashMap;
pub struct Study {}
impl Study {
    pub fn new(_name: &str) -> Self { Self {} }
    pub fn optimize<F>(&self, mut _f: F, _trials: usize) where F: FnMut(&mut Trial) -> f64 {}
    pub fn best_params(&self) -> HashMap<String, ParamValue> {
        let mut map = HashMap::new();
        map.insert("learning_rate".to_string(), ParamValue::Float(0.01));
        map.insert("batch_size".to_string(), ParamValue::Int(64));
        map
    }
}
pub struct Trial {}
impl Trial {
    pub fn suggest_float(&mut self, _name: &str, _min: f64, _max: f64) -> f64 { 0.01 }
    pub fn suggest_int(&mut self, _name: &str, _min: i32, _max: i32) -> i32 { 64 }
}
pub enum ParamValue { Float(f64), Int(i32) }
impl ParamValue {
    pub fn as_float(&self) -> Option<f64> { match self { Self::Float(f) => Some(*f), _ => None } }
    pub fn as_int(&self) -> Option<i32> { match self { Self::Int(i) => Some(*i), _ => None } }
}
''')

for crate in ["xaynet", "sealy", "arya-stark", "reflect-mcp", "optimizer"]:
    create_dummy_crate(crate)

print("Created dummy crates.")
