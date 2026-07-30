
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
