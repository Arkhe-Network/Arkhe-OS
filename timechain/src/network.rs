use crate::{EchoSignal, EvoField, PlasmaConfig, TimeBlock};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::UdpSocket;
use tokio::time::{sleep, Duration};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NetworkMessage {
    Heartbeat {
        node_id: u64,
        field_hash: [u8; 32],
        phase_time: f64,
    },
    Echo {
        echo: EchoSignal,
        block: TimeBlock,
    },
    BlockRequest {
        height: u64,
    },
}

pub struct PeerInfo {
    pub node_id: u64,
}

impl PeerInfo {
    pub fn new(node_id: u64) -> Self {
        Self { node_id }
    }
}

pub struct P2PNode {
    pub socket: Arc<UdpSocket>,
    pub node_id: u64,
    pub peers: HashMap<SocketAddr, PeerInfo>,
    pub config: PlasmaConfig,
    pub field: EvoField,
}

impl P2PNode {
    pub async fn new(addr: SocketAddr, config: PlasmaConfig) -> Self {
        let socket = Arc::new(UdpSocket::bind(addr).await.unwrap());
        let node_id = rand::random();
        let field = EvoField::harris_sheet(config);
        Self {
            socket,
            node_id,
            peers: HashMap::new(),
            config,
            field,
        }
    }

    /// Send an echo to all peers with dispersion delay
    pub async fn broadcast_echo(&mut self, echo: EchoSignal, block: TimeBlock) {
        // Emulação simples de FFT / k_dominant
        let k_dominant: f64 = 1.0;

        let packet = NetworkMessage::Echo { echo, block };
        let serialized = bincode::serialize(&packet).unwrap();

        for (peer_addr, _info) in self.peers.iter() {
            // Apply delay based on dispersion relation v_eco(k)
            let delay = 1.0 / (k_dominant.powf(1.0 / 3.0)); // v0=1, delay = 1/v
                                                            // Spawn a task to send after delay
            let socket = self.socket.clone();
            let data = serialized.clone();
            let target = *peer_addr;
            tokio::spawn(async move {
                sleep(Duration::from_secs_f64(delay * 0.1)).await; // scale for simulation
                socket.send_to(&data, target).await.unwrap();
            });
        }
    }

    /// Receive and process messages
    pub async fn run(&mut self) {
        let mut buf = vec![0u8; 65536];
        loop {
            let (len, src) = self.socket.recv_from(&mut buf).await.unwrap();
            let packet: NetworkMessage = bincode::deserialize(&buf[..len]).unwrap();
            self.handle_message(packet, src).await;
        }
    }

    pub async fn handle_message(&mut self, msg: NetworkMessage, src: SocketAddr) {
        match msg {
            NetworkMessage::Echo { echo, block } => {
                // Processamento simplificado no simulador
                self.process_echo(echo, block).await;
            }
            NetworkMessage::Heartbeat {
                node_id,
                field_hash: _,
                phase_time: _,
            } => {
                // Update peer info
                self.peers.entry(src).or_insert(PeerInfo::new(node_id));
            }
            _ => {}
        }
    }

    pub async fn process_echo(&mut self, _echo: EchoSignal, _block: TimeBlock) {
        // Implementar lógica de integração do eco (cura do campo)
    }
}
