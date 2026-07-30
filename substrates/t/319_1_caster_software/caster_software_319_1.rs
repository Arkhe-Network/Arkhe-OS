#![no_std]
extern crate alloc;

use alloc::vec::Vec;
use alloc::string::String;
use core::sync::atomic::{AtomicU32, Ordering};
use core::time::Duration;

// ─────────────────────────────────────────────────────────────────────────────
// CONSTANTES DO SUBSTRATO
// ─────────────────────────────────────────────────────────────────────────────

pub const MAX_INTERFACES: usize = 8;
pub const MAX_ROUTES: usize = 256;
pub const METRICS_WINDOW_MS: u64 = 1000;
pub const FAILOVER_LATENCY_MS: u32 = 100;
pub const FAILOVER_LOSS_PPM: u32 = 5000; // 5%
pub const FAILOVER_JITTER_US: u32 = 50000;
pub const FAILOVER_DEADLINE_US: u32 = 50_000; // 50ms
pub const COST_ETHERNET: u32 = 10;
pub const COST_WIFI: u32 = 50;
pub const COST_BLUETOOTH: u32 = 100;

pub const CASTER_OK: u32 = 0x0000_0000;
pub const CASTER_NO_ROUTE: u32 = 0x3191_0001;
pub const CASTER_ALL_DOWN: u32 = 0x3191_0002;
pub const CASTER_FAILOVER_TIMEOUT: u32 = 0x3191_0003;
pub const CASTER_POLICY_VIOLATION: u32 = 0x3191_0004;

// ─────────────────────────────────────────────────────────────────────────────
// TIPOS FUNDAMENTAIS
// ─────────────────────────────────────────────────────────────────────────────

pub type InterfaceId = [u8; 16];
pub type ArkheAddress = [u8; 64];
pub type PhysicalAddress = [u8; 48];
pub type TimestampUs = u64;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum InterfaceType {
    Ethernet = 0x01,
    WiFi2_4GHz = 0x02,
    WiFi5GHz = 0x03,
    WiFi6GHz = 0x04,
    Bluetooth = 0x05,
    Cellular = 0x06,
    Loopback = 0xFF,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum InterfaceState {
    Down = 0x00,
    Up = 0x01,
    Primary = 0x02,
    Backup = 0x03,
    Quarantined = 0x04,
}

// ─────────────────────────────────────────────────────────────────────────────
// MÉTRICAS DE CAMPO (Field Metrics)
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, Debug, Default)]
pub struct FieldMetrics {
    pub latency_us: u32,
    pub loss_ppm: u32,
    pub jitter_us: u32,
    pub throughput_kbps: u32,
    pub energy_cost: u32,
    pub signal_quality: u32,
    pub last_update_us: TimestampUs,
}

impl FieldMetrics {
    pub fn quality_score(&self) -> u32 {
        if self.latency_us == 0 || self.loss_ppm == 0 || self.jitter_us == 0 || self.energy_cost == 0 {
            return 0;
        }

        let numerator = self.throughput_kbps as u64 * 1_000_000u64;
        let denominator = (self.latency_us as u64)
            .saturating_mul(self.loss_ppm.max(1) as u64)
            .saturating_mul(self.jitter_us.max(1) as u64)
            .saturating_mul(self.energy_cost as u64);

        if denominator == 0 {
            return 0;
        }

        (numerator / denominator).min(1_000_000) as u32
    }

    pub fn is_healthy(&self) -> bool {
        self.latency_us <= FAILOVER_LATENCY_MS * 1000
            && self.loss_ppm <= FAILOVER_LOSS_PPM
            && self.jitter_us <= FAILOVER_JITTER_US
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// INTERFACE DE REDE
// ─────────────────────────────────────────────────────────────────────────────

pub struct NetworkInterface {
    pub id: InterfaceId,
    pub iface_type: InterfaceType,
    pub state: InterfaceState,
    pub physical_addr: PhysicalAddress,
    pub metrics: FieldMetrics,
    pub failure_count: u32,
    pub last_failure_us: TimestampUs,
}

impl NetworkInterface {
    pub const fn new(id: InterfaceId, iface_type: InterfaceType) -> Self {
        Self {
            id,
            iface_type,
            state: InterfaceState::Down,
            physical_addr: [0u8; 48],
            metrics: FieldMetrics {
                latency_us: u32::MAX,
                loss_ppm: 1_000_000,
                jitter_us: u32::MAX,
                throughput_kbps: 0,
                energy_cost: match iface_type {
                    InterfaceType::Ethernet => COST_ETHERNET,
                    InterfaceType::WiFi2_4GHz | InterfaceType::WiFi5GHz | InterfaceType::WiFi6GHz => COST_WIFI,
                    InterfaceType::Bluetooth => COST_BLUETOOTH,
                    _ => 100,
                },
                signal_quality: 0,
                last_update_us: 0,
            },
            failure_count: 0,
            last_failure_us: 0,
        }
    }

    pub fn update_metrics(&mut self, metrics: FieldMetrics, now_us: TimestampUs) {
        let was_healthy = self.metrics.is_healthy();
        self.metrics = metrics;
        self.metrics.last_update_us = now_us;

        let is_healthy = self.metrics.is_healthy();

        if !is_healthy {
            self.failure_count += 1;
            self.last_failure_us = now_us;
            if self.state == InterfaceState::Primary {
                self.state = InterfaceState::Up;
            }
        } else if was_healthy && self.failure_count > 0 {
            self.failure_count = self.failure_count.saturating_sub(1);
        }

        match self.state {
            InterfaceState::Down if is_healthy => {
                self.state = InterfaceState::Up;
            }
            InterfaceState::Quarantined if self.failure_count == 0 => {
                self.state = InterfaceState::Up;
            }
            _ => {}
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// INTERFACE MONITOR — Coleta de Métricas
// ─────────────────────────────────────────────────────────────────────────────

pub struct InterfaceMonitor {
    pub interfaces: [Option<NetworkInterface>; MAX_INTERFACES],
    pub count: usize,
}

impl InterfaceMonitor {
    pub const fn new() -> Self {
        const NONE: Option<NetworkInterface> = None;
        Self {
            interfaces: [NONE; MAX_INTERFACES],
            count: 0,
        }
    }

    pub fn register(&mut self, iface: NetworkInterface) -> Result<usize, u32> {
        if self.count >= MAX_INTERFACES {
            return Err(CASTER_NO_ROUTE);
        }
        let idx = self.count;
        self.interfaces[idx] = Some(iface);
        self.count += 1;
        Ok(idx)
    }

    pub fn update_interface(&mut self, idx: usize, metrics: FieldMetrics, now_us: TimestampUs) -> Result<(), u32> {
        if idx >= self.count {
            return Err(CASTER_NO_ROUTE);
        }
        if let Some(ref mut iface) = self.interfaces[idx] {
            iface.update_metrics(metrics, now_us);
            Ok(())
        } else {
            Err(CASTER_NO_ROUTE)
        }
    }

    pub fn get(&self, idx: usize) -> Option<&NetworkInterface> {
        if idx >= self.count {
            return None;
        }
        self.interfaces[idx].as_ref()
    }

    pub fn get_mut(&mut self, idx: usize) -> Option<&mut NetworkInterface> {
        if idx >= self.count {
            return None;
        }
        self.interfaces[idx].as_mut()
    }

    pub fn healthy_interfaces(&self) -> impl Iterator<Item = &NetworkInterface> {
        self.interfaces.iter()
            .filter_map(|opt| opt.as_ref())
            .filter(|iface| iface.metrics.is_healthy() && iface.state != InterfaceState::Quarantined)
    }

    pub fn active_count(&self) -> usize {
        self.interfaces.iter()
            .filter_map(|opt| opt.as_ref())
            .filter(|iface| iface.state != InterfaceState::Down)
            .count()
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// CASTER POLICY — Decisão de Roteamento
// ─────────────────────────────────────────────────────────────────────────────

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RoutingPolicy {
    MinLatency,
    MaxThroughput,
    MinEnergy,
    Balanced,
    PriorityFixed,
    ArkheAdaptive,
}

pub struct CasterPolicy {
    policy: RoutingPolicy,
    weight_latency: u32,
    weight_throughput: u32,
    weight_energy: u32,
    weight_signal: u32,
}

impl CasterPolicy {
    pub const fn new(policy: RoutingPolicy) -> Self {
        Self {
            policy,
            weight_latency: 30,
            weight_throughput: 25,
            weight_energy: 20,
            weight_signal: 25,
        }
    }

    pub fn select_interface<'a>(
        &self,
        monitor: &'a InterfaceMonitor,
    ) -> Option<(usize, &'a NetworkInterface)> {
        let mut best_idx = None;
        let mut best_score = 0u32;

        for (idx, opt) in monitor.interfaces.iter().enumerate() {
            let iface = match opt {
                Some(i) if i.metrics.is_healthy() && i.state != InterfaceState::Quarantined => i,
                _ => continue,
            };

            let score = match self.policy {
                RoutingPolicy::MinLatency => {
                    if iface.metrics.latency_us == 0 { 0 } else { 1_000_000_000 / iface.metrics.latency_us }
                }
                RoutingPolicy::MaxThroughput => {
                    iface.metrics.throughput_kbps
                }
                RoutingPolicy::MinEnergy => {
                    if iface.metrics.energy_cost == 0 { 0 } else { 1_000_000 / iface.metrics.energy_cost }
                }
                RoutingPolicy::Balanced => {
                    iface.metrics.quality_score()
                }
                RoutingPolicy::PriorityFixed => {
                    match iface.iface_type {
                        InterfaceType::Ethernet => 1000,
                        InterfaceType::WiFi2_4GHz | InterfaceType::WiFi5GHz | InterfaceType::WiFi6GHz => 500,
                        InterfaceType::Bluetooth => 100,
                        _ => 0,
                    }
                }
                RoutingPolicy::ArkheAdaptive => {
                    self.adaptive_score(iface)
                }
            };

            if score > best_score {
                best_score = score;
                best_idx = Some((idx, iface));
            }
        }

        best_idx
    }

    fn adaptive_score(&self, iface: &NetworkInterface) -> u32 {
        let m = &iface.metrics;
        let latency_norm = if m.latency_us == 0 { 0 } else { (1_000_000 / m.latency_us).min(1000) };
        let throughput_norm = (m.throughput_kbps / 1000).min(1000);
        let energy_norm = if m.energy_cost == 0 { 0 } else { (100_000 / m.energy_cost).min(1000) };
        let signal_norm = m.signal_quality.min(1000);

        (latency_norm * self.weight_latency
            + throughput_norm * self.weight_throughput
            + energy_norm * self.weight_energy
            + signal_norm * self.weight_signal) / 100
    }

    pub fn set_policy(&mut self, policy: RoutingPolicy) {
        self.policy = policy;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// ARKHE RESOLVER — Endereços Canônicos
// ─────────────────────────────────────────────────────────────────────────────

pub struct ArkheResolver {
    routes: [(ArkheAddress, usize, PhysicalAddress); MAX_ROUTES],
    route_count: usize,
}

impl ArkheResolver {
    pub const fn new() -> Self {
        Self {
            routes: [([0u8; 64], 0, [0u8; 48]); MAX_ROUTES],
            route_count: 0,
        }
    }

    pub fn register_route(
        &mut self,
        arkhe_addr: ArkheAddress,
        interface_idx: usize,
        physical_addr: PhysicalAddress,
    ) -> Result<(), u32> {
        if self.route_count >= MAX_ROUTES {
            return Err(CASTER_NO_ROUTE);
        }
        self.routes[self.route_count] = (arkhe_addr, interface_idx, physical_addr);
        self.route_count += 1;
        Ok(())
    }

    pub fn resolve(&self, arkhe_addr: &ArkheAddress) -> Option<(usize, &PhysicalAddress)> {
        for i in 0..self.route_count {
            if self.routes[i].0 == *arkhe_addr {
                return Some((self.routes[i].1, &self.routes[i].2));
            }
        }
        None
    }

    pub fn parse_address(addr_str: &str) -> Option<ArkheAddress> {
        if !addr_str.starts_with("arkhe://") {
            return None;
        }
        let mut addr = [0u8; 64];
        let bytes = addr_str.as_bytes();
        let len = bytes.len().min(63);
        addr[..len].copy_from_slice(&bytes[..len]);
        Some(addr)
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// FAILOVER ENGINE — Switch Determinístico <50ms
// ─────────────────────────────────────────────────────────────────────────────

pub struct FailoverEngine {
    pub primary_idx: Option<usize>,
    pub backup_idx: Option<usize>,
    pub failover_count: u64,
    pub last_failover_us: TimestampUs,
    pub in_progress: bool,
}

impl FailoverEngine {
    pub const fn new() -> Self {
        Self {
            primary_idx: None,
            backup_idx: None,
            failover_count: 0,
            last_failover_us: 0,
            in_progress: false,
        }
    }

    pub fn init(&mut self, primary: usize, backup: Option<usize>) {
        self.primary_idx = Some(primary);
        self.backup_idx = backup;
    }

    pub fn check_and_failover(
        &mut self,
        monitor: &InterfaceMonitor,
        policy: &CasterPolicy,
        now_us: TimestampUs,
    ) -> Result<(usize, bool), u32> {
        let primary_healthy = self.primary_idx
            .and_then(|idx| monitor.get(idx))
            .map(|iface| iface.metrics.is_healthy())
            .unwrap_or(false);

        if primary_healthy && !self.in_progress {
            return Ok((self.primary_idx.unwrap(), false));
        }

        if self.in_progress {
            if now_us.saturating_sub(self.last_failover_us) > FAILOVER_DEADLINE_US as u64 {
                return Err(CASTER_FAILOVER_TIMEOUT);
            }
            if let Some(backup) = self.backup_idx {
                return Ok((backup, true));
            }
        }

        self.in_progress = true;
        self.last_failover_us = now_us;

        match policy.select_interface(monitor) {
            Some((idx, _)) => {
                self.primary_idx = Some(idx);
                self.failover_count += 1;
                self.in_progress = false;
                Ok((idx, true))
            }
            None => {
                self.in_progress = false;
                Err(CASTER_ALL_DOWN)
            }
        }
    }

    pub fn force_failover(&mut self, new_primary: usize) {
        self.primary_idx = Some(new_primary);
        self.failover_count += 1;
        self.in_progress = false;
    }

    pub fn failover_count(&self) -> u64 {
        self.failover_count
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// UNIFIED TUNNEL — WireGuard como Cripto-Trivium Software
// ─────────────────────────────────────────────────────────────────────────────

pub struct UnifiedTunnel {
    pub local_pubkey: [u8; 3952],
    pub local_privkey: [u8; 128],
    pub active_interface: Option<usize>,
    pub state: TunnelState,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TunnelState {
    Down,
    Handshaking,
    Established,
    Rekeying,
    Error,
}

impl UnifiedTunnel {
    pub const fn new() -> Self {
        Self {
            local_pubkey: [0u8; 3952],
            local_privkey: [0u8; 128],
            active_interface: None,
            state: TunnelState::Down,
        }
    }

    pub fn init(&mut self, pubkey: [u8; 3952], privkey: [u8; 128]) {
        self.local_pubkey = pubkey;
        self.local_privkey = privkey;
        self.state = TunnelState::Down;
    }

    pub fn establish(&mut self, interface_idx: usize) -> Result<(), u32> {
        self.active_interface = Some(interface_idx);
        self.state = TunnelState::Handshaking;
        self.state = TunnelState::Established;
        Ok(())
    }

    pub fn migrate(&mut self, new_interface_idx: usize) -> Result<(), u32> {
        let old_idx = self.active_interface;
        self.active_interface = Some(new_interface_idx);
        if old_idx.is_some() {
            Ok(())
        } else {
            self.establish(new_interface_idx)
        }
    }

    pub fn teardown(&mut self) {
        for byte in self.local_privkey.iter_mut() {
            *byte = 0;
        }
        self.state = TunnelState::Down;
        self.active_interface = None;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// OSAL - HAL ABSTRACTIONS
// ─────────────────────────────────────────────────────────────────────────────

pub trait OsMetricsProvider: Send + Sync {
    fn collect_metrics(&self, iface_id: &InterfaceId) -> Result<FieldMetrics, u32>;
}

pub trait OsTunnelProvider: Send + Sync {
    fn setup_tunnel(&mut self, iface_idx: usize, pubkey: &[u8], privkey: &[u8]) -> Result<(), u32>;
    fn migrate_tunnel(&mut self, new_iface_idx: usize) -> Result<(), u32>;
    fn teardown_tunnel(&mut self) -> Result<(), u32>;
}

// ─────────────────────────────────────────────────────────────────────────────
// CASTER ORQUESTRADOR — Integração completa
// ─────────────────────────────────────────────────────────────────────────────

pub struct CasterOrchestrator<M: OsMetricsProvider, T: OsTunnelProvider> {
    pub monitor: InterfaceMonitor,
    pub policy: CasterPolicy,
    pub resolver: ArkheResolver,
    pub failover: FailoverEngine,
    pub tunnel: UnifiedTunnel,

    pub metrics_provider: M,
    pub tunnel_provider: T,

    pub messages_routed: u64,
    pub bytes_transferred: u64,
    pub last_tick_us: TimestampUs,
}

impl<M: OsMetricsProvider, T: OsTunnelProvider> CasterOrchestrator<M, T> {
    pub fn new(policy: RoutingPolicy, metrics_provider: M, tunnel_provider: T) -> Self {
        Self {
            monitor: InterfaceMonitor::new(),
            policy: CasterPolicy::new(policy),
            resolver: ArkheResolver::new(),
            failover: FailoverEngine::new(),
            tunnel: UnifiedTunnel::new(),
            metrics_provider,
            tunnel_provider,
            messages_routed: 0,
            bytes_transferred: 0,
            last_tick_us: 0,
        }
    }

    pub fn tick(&mut self, now_us: TimestampUs) -> Result<(), u32> {
        self.last_tick_us = now_us;

        // 1. Verifica saúde das interfaces (usando OS Provider em vez de STUB)
        for i in 0..self.monitor.count {
            if let Some(iface) = &self.monitor.interfaces[i] {
                if let Ok(new_metrics) = self.metrics_provider.collect_metrics(&iface.id) {
                    self.monitor.update_interface(i, new_metrics, now_us)?;
                }
            }
        }

        let (active_idx, _did_failover) = self.failover.check_and_failover(
            &self.monitor,
            &self.policy,
            now_us,
        )?;

        if self.tunnel.active_interface != Some(active_idx) {
            self.tunnel.migrate(active_idx)?;
            self.tunnel_provider.migrate_tunnel(active_idx)?;
        }

        self.messages_routed += 1;

        Ok(())
    }

    pub fn route_message(
        &mut self,
        dest: &ArkheAddress,
        payload: &[u8],
    ) -> Result<usize, u32> {
        let (iface_idx, _phys_addr) = self.resolver.resolve(dest)
            .ok_or(CASTER_NO_ROUTE)?;

        if self.failover.primary_idx != Some(iface_idx) {
            let iface = self.monitor.get(iface_idx)
                .ok_or(CASTER_NO_ROUTE)?;
            if !iface.metrics.is_healthy() {
                return Err(CASTER_ALL_DOWN);
            }
        }

        self.bytes_transferred += payload.len() as u64;
        self.messages_routed += 1;

        Ok(iface_idx)
    }

    pub fn add_interface(&mut self, iface: NetworkInterface) -> Result<usize, u32> {
        self.monitor.register(iface)
    }

    pub fn set_failover(&mut self, primary: usize, backup: Option<usize>) {
        self.failover.init(primary, backup);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// TESTES E MOCKS
// ─────────────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    struct MockMetricsProvider;
    impl OsMetricsProvider for MockMetricsProvider {
        fn collect_metrics(&self, _iface_id: &InterfaceId) -> Result<FieldMetrics, u32> {
            Ok(FieldMetrics {
                latency_us: 1000,
                loss_ppm: 100,
                jitter_us: 1000,
                throughput_kbps: 100_000,
                energy_cost: COST_ETHERNET,
                signal_quality: 60,
                last_update_us: 1_000_000,
            })
        }
    }

    struct MockTunnelProvider;
    impl OsTunnelProvider for MockTunnelProvider {
        fn setup_tunnel(&mut self, _idx: usize, _pub: &[u8], _priv: &[u8]) -> Result<(), u32> { Ok(()) }
        fn migrate_tunnel(&mut self, _idx: usize) -> Result<(), u32> { Ok(()) }
        fn teardown_tunnel(&mut self) -> Result<(), u32> { Ok(()) }
    }

    fn make_iface(id_byte: u8, iface_type: InterfaceType) -> NetworkInterface {
        let mut id = [0u8; 16];
        id[0] = id_byte;
        NetworkInterface::new(id, iface_type)
    }

    #[test]
    fn test_caster_orchestrator_with_mocks() {
        let mut caster = CasterOrchestrator::new(
            RoutingPolicy::ArkheAdaptive,
            MockMetricsProvider,
            MockTunnelProvider,
        );

        let mut eth = make_iface(0x01, InterfaceType::Ethernet);
        eth.update_metrics(FieldMetrics::default(), 1_000_000);
        let eth_idx = caster.add_interface(eth).unwrap();

        caster.set_failover(eth_idx, None);

        let result = caster.tick(2_000_000);
        assert!(result.is_ok());
    }
}
