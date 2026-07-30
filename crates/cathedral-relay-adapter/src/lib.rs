pub mod client;
pub mod vault;
pub mod bridge;
pub mod types;
pub mod error;

pub use client::RelayIndexerClient;
pub use vault::RelayVault;
pub use bridge::RelayBridge;
pub use types::*;
pub use error::RelayError;

pub type Result<T> = std::result::Result<T, RelayError>;

use alloy::primitives::Address;

pub struct RelayAdapter {
    pub indexer: RelayIndexerClient,
    pub vault: RelayVault,
    pub bridge: RelayBridge,
}

impl RelayAdapter {
    pub async fn new(
        rpc_url: &str,
        indexer_url: &str,
        vault_address: Address,
        bridge_address: Address,
        chain_id: u64,
    ) -> Result<Self> {
        let indexer = RelayIndexerClient::new(indexer_url);
        let vault = RelayVault::new(rpc_url, vault_address, chain_id).await?;
        let bridge = RelayBridge::new(rpc_url, bridge_address, chain_id).await?;

        Ok(Self {
            indexer,
            vault,
            bridge,
        })
    }

    pub async fn get_total_balance(
        &self,
        user: Address,
        asset: Address,
    ) -> Result<BalanceInfo> {
        let total_assets = self.vault.convert_to_assets(user).await?;
        let yield_earned = self.indexer.get_yield_earned(user, AssetAddress(asset)).await?;
        Ok(BalanceInfo {
            total_assets,
            yield_earned,
            pending_rewards: alloy::primitives::U256::ZERO,
        })
    }
}
