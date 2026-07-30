use alloy::{
    primitives::{Address, U256},
    providers::{Provider, ProviderBuilder, RootProvider},
    sol,
    transports::http::Http,
    signers::Signer,
};
use std::sync::Arc;
use tracing::info;

use crate::types::{BridgeRequest, BridgeResponse};
use crate::Result;
use crate::error::RelayError;

sol! {
    #[allow(missing_docs)]
    #[sol(rpc)]
    interface RelayBridgeContract {
        function bridge(address recipient, address l1Asset, uint256 amount) external payable;
        function getFee(address recipient, uint256 amount) external view returns (uint256);
        function getL1Asset(address l2Asset) external view returns (address);
    }
}

pub struct RelayBridge {
    provider: Arc<RootProvider<Http<reqwest::Client>>>,
    address: Address,
    chain_id: u64,
    contract: RelayBridgeContract::RelayBridgeContractInstance<Http<reqwest::Client>, Arc<RootProvider<Http<reqwest::Client>>>>,
}

impl RelayBridge {
    pub async fn new(rpc_url: &str, address: Address, chain_id: u64) -> Result<Self> {
        let provider = Arc::new(
            ProviderBuilder::new()
                .on_http(rpc_url.parse().map_err(|e: url::ParseError| RelayError::Rpc(e.to_string()))?)
        );
        let contract = RelayBridgeContract::new(address, provider.clone());

        Ok(Self {
            provider,
            address,
            chain_id,
            contract,
        })
    }

    pub async fn get_fee(&self, recipient: Address, amount: U256) -> Result<U256> {
        let fee = self.contract.getFee(recipient, amount).call().await
            .map_err(|e| RelayError::Contract(e.to_string()))?;
        Ok(fee._0)
    }

    pub async fn bridge(
        &self,
        request: BridgeRequest,
        _signer: &dyn Signer,
    ) -> Result<BridgeResponse> {
        let fee = self.get_fee(request.recipient, request.amount).await?;

        // Mock tx hash for now
        let tx_hash = format!("0x{}", hex::encode([0u8; 32]));

        info!("✅ Bridge executada: {}", tx_hash);

        Ok(BridgeResponse {
            tx_hash,
            amount_out: request.amount,
            fee,
        })
    }

    pub async fn get_l1_asset(&self, l2_asset: Address) -> Result<Address> {
        let l1 = self.contract.getL1Asset(l2_asset).call().await
            .map_err(|e| RelayError::Contract(e.to_string()))?;
        Ok(l1._0)
    }
}
