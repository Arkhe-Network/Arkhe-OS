#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HeaderType {
    PqcAttestation,
}
pub struct ArkheObject {
    pub data: String,
    pub did: String,
    pub headers: Vec<(HeaderType, Vec<u8>)>,
}
impl ArkheObject {
    pub fn new(data: String, did: &str) -> Self {
        Self {
            data,
            did: did.to_string(),
            headers: vec![],
        }
    }
    pub fn add_header(&mut self, typ: HeaderType, val: Vec<u8>) {
        self.headers.push((typ, val));
    }
    pub fn get_header(&self, typ: HeaderType) -> Option<&[u8]> {
        self.headers
            .iter()
            .find(|(t, _)| *t == typ)
            .map(|(_, v)| v.as_slice())
    }
}
