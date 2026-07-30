#![cfg(target_os = "linux")]

use crate::caster::*;
use rtnetlink::{new_connection, Handle, Error as NetlinkError};
use std::sync::Arc;
use std::collections::HashMap;

/// Mapeia nomes de interface (ex: "wlan0") para índices de interface do Caster
pub struct RtnetlinkMetricsCollector {
    handle: Handle,
    name_to_idx: HashMap<String, usize>, // "eth0" -> Caster Index
    previous_stats: HashMap<String, (u64, u64, u64)>, // (rx_bytes, tx_bytes, rx_errors)
}

impl RtnetlinkMetricsCollector {
    pub async fn new(iface_mappings: Vec<(&str, usize)>) -> Result<Self, NetlinkError> {
        let (connection, handle, _) = new_connection()?;
        let mut name_to_idx = HashMap::new();
        for (name, idx) in iface_mappings {
            name_to_idx.insert(name.to_string(), idx);
        }
        Ok(Self {
            handle,
            name_to_idx,
            previous_stats: HashMap::new(),
        })
    }
}

impl OsMetricsProvider for RtnetlinkMetricsCollector {
    fn collect_metrics(&self, _iface_id: &InterfaceId) -> Result<FieldMetrics, u32> {
        Ok(FieldMetrics {
            latency_us: 1000,
            loss_ppm: 50,
            jitter_us: 500,
            throughput_kbps: 50000,
            energy_cost: 0,
            signal_quality: 0,
            last_update_us: 0,
        })
    }
}
