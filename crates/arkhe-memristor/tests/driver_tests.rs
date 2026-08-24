use arkhe_memristor::{MemristorDriver, Memristor, DriverConfig, ResistanceState};

#[test]
fn test_default_config() {
    let config = DriverConfig::default();
    assert_eq!(config.voltage, 0.09);
    assert_eq!(config.compliance_current, 100e-6);
}

#[test]
fn test_driver_state_machine() {
    let mem = MemristorDriver::new();
    // Default should start in High (OFF) state, but it is not initialized yet.
    assert!(!mem.is_initialized());

    // So we initialize it properly
    let mut mem = MemristorDriver::with_config(DriverConfig::default()).unwrap();
    assert_eq!(mem.read().unwrap(), ResistanceState::High);

    // Perform a SET operation
    mem.set(None).unwrap();
    assert_eq!(mem.read().unwrap(), ResistanceState::Low);

    // Perform a RESET operation
    mem.reset(None).unwrap();
    assert_eq!(mem.read().unwrap(), ResistanceState::High);
}
