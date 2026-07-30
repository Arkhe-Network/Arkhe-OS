use alloy::{
    primitives::{Address, U256},
    providers::{Provider, ProviderBuilder, RootProvider},
    sol,
    transports::http::Http,
    signers::Signer,
};
use std::sync::Arc;

use crate::types::{VaultInfo, AssetAddress};
use crate::Result;
use crate::error::RelayError;

sol! {
    #[allow(missing_docs)]
    #[sol(rpc)]
    interface IERC4626 {
        function asset() external view returns (address);
        function totalAssets() external view returns (uint256);
        function convertToShares(uint256 assets) external view returns (uint256);
        function convertToAssets(uint256 shares) external view returns (uint256);
        function maxDeposit(address receiver) external view returns (uint256);
        function deposit(uint256 assets, address receiver) external returns (uint256);
        function redeem(uint256 shares, address receiver, address owner) external returns (uint256);
        function withdraw(uint256 assets, address receiver, address owner) external returns (uint256);
    }

    #[allow(missing_docs)]
    #[sol(rpc)]
    interface IERC20 {
        function approve(address spender, uint256 amount) external returns (bool);
        function balanceOf(address owner) external view returns (uint256);
        function allowance(address owner, address spender) external view returns (uint256);
    }
}

pub struct RelayVault {
    provider: Arc<RootProvider<Http<reqwest::Client>>>,
    address: Address,
    chain_id: u64,
    contract: IERC4626::IERC4626Instance<Http<reqwest::Client>, Arc<RootProvider<Http<reqwest::Client>>>>,
}

impl RelayVault {
    pub async fn new(rpc_url: &str, address: Address, chain_id: u64) -> Result<Self> {
        let provider = Arc::new(
            ProviderBuilder::new()
                .on_http(rpc_url.parse().map_err(|e: url::ParseError| RelayError::Rpc(e.to_string()))?)
        );

        let contract = IERC4626::new(address, provider.clone());

        Ok(Self {
            provider,
            address,
            chain_id,
            contract,
        })
    }

    pub async fn get_info(&self) -> Result<VaultInfo> {
        let asset = self.contract.asset().call().await
            .map_err(|e| RelayError::Contract(e.to_string()))?;
        let total_assets = self.contract.totalAssets().call().await
            .map_err(|e| RelayError::Contract(e.to_string()))?;

        Ok(VaultInfo {
            address: self.address,
            asset: AssetAddress(asset._0),
            name: format!("Relay Vault {}", hex::encode(self.address)),
            symbol: "rvETH".to_string(),
            decimals: 18,
            total_supply: U256::ZERO,
            total_assets: total_assets._0,
            apy: Some(0.05),
        })
    }

    pub async fn convert_to_assets(&self, owner: Address) -> Result<U256> {
        let shares = self.get_user_shares(owner).await?;
        let assets = self.contract.convertToAssets(shares).call().await
            .map_err(|e| RelayError::Contract(e.to_string()))?;
        Ok(assets._0)
    }

    async fn get_user_shares(&self, owner: Address) -> Result<U256> {
        let erc20 = IERC20::new(self.address, self.provider.clone());
        let balance = erc20.balanceOf(owner).call().await
            .map_err(|e| RelayError::Contract(e.to_string()))?;
        Ok(balance._0)
    }

    pub async fn deposit(
        &self,
        amount: U256,
        _receiver: Address,
        _signer: &dyn Signer,
    ) -> Result<U256> {
        // Mock
        Ok(amount)
    }

    pub async fn redeem(
        &self,
        shares: U256,
        _receiver: Address,
        _owner: Address,
        _signer: &dyn Signer,
    ) -> Result<U256> {
         let assets = self.contract.convertToAssets(shares).call().await
            .map_err(|e| RelayError::Contract(e.to_string()))?;
        Ok(assets._0)
    }
}
