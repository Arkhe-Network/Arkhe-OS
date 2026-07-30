use cathedral_33t::tensor::Tensor;

#[test]
fn test_zeros() {
    let t = Tensor::zeros(&[2, 3]);
    assert_eq!(t.shape(), vec![2, 3]);
}
