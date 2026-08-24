use arkhe_memristor::integration::MemristorStorage;

#[test]
fn test_memristor_storage_basic() {
    let mut storage = MemristorStorage::new();

    // Write value 0x5A to address 10
    storage.write_byte(10, 0x5A).unwrap();

    // Read the value back
    let value = storage.read_byte(10).unwrap();

    // Check if the lower 3 bits are preserved correctly (0x5A & 0x07 = 2)
    assert_eq!(value & 0x07, 0x5A & 0x07);
    assert_eq!(value, 0x5A);
}
