/// ARKHE Python bindings — PyO3 bridge stub.
pub fn version() -> &'static str {
    "6.1.0"
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_version() {
        assert_eq!(super::version(), "6.1.0");
    }
}
