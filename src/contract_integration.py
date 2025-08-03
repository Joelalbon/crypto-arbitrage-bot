"""
Contract Integration Module
Handles interaction with the FlashLoanArbitrage smart contract
"""

import asyncio
import json
import os
from typing import Dict, Optional, List
from web3 import Web3
from eth_account import Account
from eth_utils import to_checksum_address
import logging

logger = logging.getLogger(__name__)

class ContractIntegration:
    def __init__(self, network: str = "polygon"):
        self.network = network
        self.web3 = None
        self.contract = None
        self.account = None
        self.contract_address = None
        
        # Network configurations
        self.network_configs = {
            "polygon": {
                "rpc": os.getenv("POLYGON_RPC", "https://polygon-rpc.com"),
                "explorer": "https://polygonscan.com",
                "chain_id": 137
            },
            "bsc": {
                "rpc": os.getenv("BSC_RPC", "https://bsc-dataseed.binance.org"),
                "explorer": "https://bscscan.com",
                "chain_id": 56
            },
            "avalanche": {
                "rpc": os.getenv("AVALANCHE_RPC", "https://api.avax.network/ext/bc/C/rpc"),
                "explorer": "https://snowtrace.io",
                "chain_id": 43114
            }
        }
        
        # Load contract ABI
        self.contract_abi = self._load_contract_abi()
        
    def _load_contract_abi(self) -> List[Dict]:
        """Load contract ABI"""
        return [
            {
                "inputs": [{"internalType": "address", "name": "_addressProvider", "type": "address"}],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "inputs": [
                    {"components": [
                        {"internalType": "address", "name": "tokenA", "type": "address"},
                        {"internalType": "address", "name": "tokenB", "type": "address"},
                        {"internalType": "uint256", "name": "amount", "type": "uint256"},
                        {"internalType": "address", "name": "dexRouter1", "type": "address"},
                        {"internalType": "address", "name": "dexRouter2", "type": "address"},
                        {"internalType": "uint256", "name": "minProfit", "type": "uint256"}
                    ], "internalType": "struct FlashLoanArbitrage.ArbitrageParams", "name": "params", "type": "tuple"}
                ],
                "name": "executeArbitrage",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "token", "type": "address"}],
                "name": "getBalance",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "token", "type": "address"}],
                "name": "isTokenWhitelisted",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "bot", "type": "address"}],
                "name": "isBotAuthorized",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "address", "name": "router", "type": "address"}],
                "name": "isDexRouterWhitelisted",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def initialize(self, contract_address: str, private_key: str):
        """Initialize Web3 connection and contract"""
        try:
            if self.network not in self.network_configs:
                raise ValueError(f"Unsupported network: {self.network}")
            
            config = self.network_configs[self.network]
            
            # Initialize Web3
            self.web3 = Web3(Web3.HTTPProvider(config["rpc"]))
            if not self.web3.isConnected():
                raise ConnectionError(f"Failed to connect to {self.network}")
            
            # Set up account
            self.account = Account.from_key(private_key)
            self.web3.eth.default_account = self.account.address
            
            # Set contract address
            self.contract_address = to_checksum_address(contract_address)
            
            # Initialize contract
            self.contract = self.web3.eth.contract(
                address=self.contract_address,
                abi=self.contract_abi
            )
            
            logger.info(f"Contract integration initialized for {self.network}")
            logger.info(f"Contract address: {self.contract_address}")
            logger.info(f"Account: {self.account.address}")
            
        except Exception as e:
            logger.error(f"Failed to initialize contract integration: {e}")
            raise
    
    async def execute_arbitrage(self, token_a: str, token_b: str, amount: int, 
                              dex_router1: str, dex_router2: str, min_profit: int) -> str:
        """Execute arbitrage using flashloan"""
        try:
            # Build transaction
            tx = self.contract.functions.executeArbitrage({
                "tokenA": to_checksum_address(token_a),
                "tokenB": to_checksum_address(token_b),
                "amount": amount,
                "dexRouter1": to_checksum_address(dex_router1),
                "dexRouter2": to_checksum_address(dex_router2),
                "minProfit": min_profit
            }).buildTransaction({
                "from": self.account.address,
                "nonce": self.web3.eth.getTransactionCount(self.account.address),
                "gas": 5000000,
                "gasPrice": self.web3.toWei("30", "gwei")
            })
            
            # Sign transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.account.key)
            
            # Send transaction
            tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)
            
            # Wait for receipt
            receipt = self.web3.eth.waitForTransactionReceipt(tx_hash)
            
            if receipt.status == 1:
                logger.info(f"Arbitrage executed successfully: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                raise Exception("Transaction failed")
                
        except Exception as e:
            logger.error(f"Failed to execute arbitrage: {e}")
            raise
    
    async def get_contract_balance(self, token_address: str) -> int:
        """Get token balance in contract"""
        try:
            balance = self.contract.functions.getBalance(
                to_checksum_address(token_address)
            ).call()
            return balance
        except Exception as e:
            logger.error(f"Failed to get contract balance: {e}")
            raise
    
    async def is_token_whitelisted(self, token_address: str) -> bool:
        """Check if token is whitelisted"""
        try:
            return self.contract.functions.isTokenWhitelisted(
                to_checksum_address(token_address)
            ).call()
        except Exception as e:
            logger.error(f"Failed to check token whitelist: {e}")
            raise
    
    async def is_bot_authorized(self, bot_address: str) -> bool:
        """Check if bot is authorized"""
        try:
            return self.contract.functions.isBotAuthorized(
                to_checksum_address(bot_address)
            ).call()
        except Exception as e:
            logger.error(f"Failed to check bot authorization: {e}")
            raise
    
    async def is_dex_router_whitelisted(self, router_address: str) -> bool:
        """Check if DEX router is whitelisted"""
        try:
            return self.contract.functions.isDexRouterWhitelisted(
                to_checksum_address(router_address)
            ).call()
        except Exception as e:
            logger.error(f"Failed to check DEX router whitelist: {e}")
            raise
    
    async def get_gas_price(self) -> int:
        """Get current gas price"""
        try:
            return self.web3.eth.gas_price
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            raise
    
    async def get_transaction_receipt(self, tx_hash: str) -> Dict:
        """Get transaction receipt"""
        try:
            return self.web3.eth.getTransactionReceipt(tx_hash)
        except Exception as e:
            logger.error(f"Failed to get transaction receipt: {e}")
            raise
    
    def get_explorer_url(self, tx_hash: str) -> str:
        """Get explorer URL for transaction"""
        config = self.network_configs[self.network]
        return f"{config['explorer']}/tx/{tx_hash}"

# Example usage
async def main():
    """Example usage of contract integration"""
    
    # Initialize contract integration
    contract_integration = ContractIntegration("polygon")
    
    # Replace with actual values
    contract_address = "0x..."  # Your deployed contract address
    private_key = os.getenv("POLYGON_PRIVATE_KEY")
    
    await contract_integration.initialize(contract_address, private_key)
    
    # Example arbitrage parameters
    token_a = "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"  # WETH on Polygon
    token_b = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC on Polygon
    amount = 1000 * 10**18  # 1000 tokens
    dex_router1 = "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"  # QuickSwap
    dex_router2 = "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"  # SushiSwap
    min_profit = 10 * 10**18  # Minimum 10 tokens profit
    
    # Execute arbitrage
    tx_hash = await contract_integration.execute_arbitrage(
        token_a, token_b, amount, dex_router1, dex_router2, min_profit
    )
    
    print(f"Arbitrage transaction: {tx_hash}")
    print(f"Explorer URL: {contract_integration.get_explorer_url(tx_hash)}")

if __name__ == "__main__":
    asyncio.run(main())