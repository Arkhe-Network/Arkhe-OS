pub struct AtomSpace;
impl AtomSpace {
    pub fn new() -> Self { Self }
    pub fn add(&mut self, _atom: ExpressionAtom) {}
    pub fn query(&self, _pattern: &ExpressionAtom) -> Vec<Atom> { vec![] }
}

pub struct ExpressionAtom;
impl ExpressionAtom {
    pub fn new(_sym: Symb, _args: Vec<Value>) -> Self { Self }
}

pub struct Symb;
impl Symb {
    pub fn new(_s: &str) -> Self { Self }
}

pub struct Value;
impl Value {
    pub fn from<T>(_val: T) -> Self { Self }
}

pub struct Var;
impl Var {
    pub fn new(_s: &str) -> Self { Self }
}

impl From<Var> for Value {
    fn from(_v: Var) -> Self { Value }
}

pub enum Atom {
    Expression(Expression),
}
impl Atom {
    pub fn as_expression(&self) -> Option<&Expression> {
        match self {
            Self::Expression(e) => Some(e),
        }
    }
}

pub struct Expression;
impl Expression {
    pub fn args(&self) -> Vec<Arg> { vec![] }
}

pub struct Arg;
impl Arg {
    pub fn as_number(&self) -> Option<f64> { None }
    pub fn as_string(&self) -> Option<&str> { None }
}
