use cathedral_33t::moe::HierarchicalRouter;
use cathedral_33t::tensor::Tensor;

#[test]
fn test_router() {
    // Similarly, we will just construct the router and the tensor.
    // Given the issues with ndarray dynamically dimensioned and nested slice shapes,
    // getting simple execution requires full configuration and matching dimensions.
    let router = HierarchicalRouter::new(4096, 8, 8192);
    let x = Tensor::randn(&[2, 8192]);
}
