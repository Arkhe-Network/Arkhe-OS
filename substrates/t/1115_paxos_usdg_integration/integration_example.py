# integration_example.py
import asyncio
import logging
from decimal import Decimal
from paxos_gateway import PaxosUSDGGateway, PaxosCredentials

logging.basicConfig(level=logging.INFO)

async def main():
    # Configurações (use variaveis de ambiente em producao)
    creds = PaxosCredentials(
        client_id="SEU_CLIENT_ID",
        client_secret="SEU_CLIENT_SECRET",
        api_base_url="https://api.paxos.com/v2",  # ou sandbox
        web3_provider_url="https://mainnet.infura.io/v3/SUA_KEY",
        usdg_contract_address="0x...",  # endereco do contrato USDG
        private_key="0x..."  # mantenha em segredo
    )

    async with PaxosUSDGGateway(creds) as gateway:
        # Registra callback de alerta (ex: enviar notificacao para Windows)
        async def alert_callback(title: str, message: str, severity: str):
            logging.warning("[ALERTA {0}] {1}: {2}".format(severity.upper(), title, message))
        gateway.set_alert_callback(alert_callback)

        # Inicia monitoramento
        await gateway.start_monitoring(interval_seconds=30)

        # 1. Consultar saldos custodiais
        balances = await gateway.get_balances()
        for bal in balances:
            print("Saldo {0}: total={1}, disponivel={2}".format(bal.currency, bal.total, bal.available))

        # 2. Mint de 1000 USDG
        tx_mint = await gateway.mint(Decimal("1000"), currency="USD")
        print("Mint iniciado: {0}, status={1}".format(tx_mint.id, tx_mint.status))

        # 3. Transferencia on-chain
        tx_hash = await gateway.transfer_on_chain("0xDestino...", Decimal("100"))
        print("Transferencia enviada: {0}".format(tx_hash))

        # 4. Aumentar allowance para um contrato de swap
        spender = "0xContratoSwap..."
        await gateway.increase_allowance(spender, Decimal("500"))

        # 5. Consultar saldo on-chain
        onchain_bal = await gateway.get_onchain_balance()
        print("Saldo on-chain da carteira: {0} USDG".format(onchain_bal))

        # 6. Redeem (resgatar USDG para USD)
        tx_redeem = await gateway.redeem(Decimal("200"), destination_currency="USD")
        print("Redeem iniciado: {0}".format(tx_redeem.id))

        # Aguardar monitoramento por alguns segundos
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
