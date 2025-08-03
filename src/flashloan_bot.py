"""
FlashLoan Bot Extension
Enhanced arbitrage bot with flashloan capabilities
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import aiohttp
from web3 import Web3
from eth_utils import to_checksum_address

from src.contract_integration import ContractIntegration
from src.monitorbot import ArbitrageBot
from src.slack_bot import SlackBot

logger = logging.getLogger(__name__)

class FlashLoanBot(ArbitrageBot):
    def __init__(self, config_path: str = "config.json"):
        super().__init__(config_path)
        self.contract_integration = None
        self.flashloan_enabled = False
        self.contract_address = None
        self.min_profit_threshold = Decimal("0.01")  # Minimum profit in ETH
        self.max_loan_amount = Decimal("1000")  # Maximum loan amount
        
    async def initialize_flashloan(self, network: str, contract_address: str, private_key: str):
        """Initialize flashloan capabilities"""
        try:
            self.contract_integration = ContractIntegration(network)
            await self.contract_integration.initialize(contract_address, private_key)
            self.contract_address = contract_address
            self.flashloan_enabled = True
            
            logger.info(f"Flashloan initialized for {network}")
            logger.info(f"Contract address: {contract_address}")
            
            # Send notification
            if hasattr(self, 'slack_bot') and self.slack_bot:
                await self.slack_bot.send_notification(
                    f"🚀 Flashloan bot initialized on {network}\n"
                    f"Contract: `{contract_address}`"
                )
                
        except Exception as e:
            logger.error(f"Failed to initialize flashloan: {e}")
            raise
    
    async def find_arbitrage_opportunities_with_flashloan(self) -> List[Dict]:
        """Find arbitrage opportunities suitable for flashloan execution"""
        opportunities = []
        
        # Get regular arbitrage opportunities
        regular_opps = await self.find_arbitrage_opportunities()
        
        for opp in regular_opps:
            # Calculate if flashloan makes sense
            profit_after_fees = await self.calculate_flashloan_profit(opp)
            
            if profit_after_fees > self.min_profit_threshold:
                flashloan_opp = {
                    **opp,
                    "flashloan_profit": profit_after_fees,
                    "loan_amount": self.calculate_optimal_loan_amount(opp),
                    "execution_method": "flashloan"
                }
                opportunities.append(flashloan_opp)
        
        return opportunities
    
    async def calculate_flashloan_profit(self, opportunity: Dict) -> Decimal:
        """Calculate profit after flashloan fees"""
        profit = Decimal(str(opportunity.get('profit', 0)))
        
        # Calculate flashloan fee (typically 0.09% on Aave)
        flashloan_fee_rate = Decimal("0.0009")  # 0.09%
        loan_amount = self.calculate_optimal_loan_amount(opportunity)
        flashloan_fee = loan_amount * flashloan_fee_rate
        
        # Calculate gas costs
        gas_cost = await self.estimate_gas_cost()
        
        # Net profit calculation
        net_profit = profit - flashloan_fee - gas_cost
        
        return net_profit
    
    async def calculate_optimal_loan_amount(self, opportunity: Dict) -> Decimal:
        """Calculate optimal loan amount for maximum profit"""
        # This is a simplified calculation
        # In practice, this would consider liquidity, slippage, and gas costs
        
        base_amount = Decimal(str(opportunity.get('amount', 100)))
        profit_rate = Decimal(str(opportunity.get('profit_rate', 0.01)))
        
        # Calculate loan amount that maximizes profit after fees
        optimal_loan = min(
            base_amount * 10,  # Scale up based on opportunity
            self.max_loan_amount
        )
        
        return optimal_loan
    
    async def estimate_gas_cost(self) -> Decimal:
        """Estimate gas cost for flashloan transaction"""
        try:
            gas_price = await self.contract_integration.get_gas_price()
            estimated_gas = 500000  # Estimated gas for flashloan + trades
            
            # Convert to ETH
            gas_cost_wei = gas_price * estimated_gas
            gas_cost_eth = Decimal(str(Web3.fromWei(gas_cost_wei, 'ether')))
            
            return gas_cost_eth
            
        except Exception as e:
            logger.error(f"Failed to estimate gas cost: {e}")
            return Decimal("0.01")  # Default fallback
    
    async def execute_flashloan_arbitrage(self, opportunity: Dict) -> Dict:
        """Execute arbitrage using flashloan"""
        if not self.flashloan_enabled:
            raise Exception("Flashloan not initialized")
        
        try:
            # Prepare parameters
            token_a = opportunity['token_a']['address']
            token_b = opportunity['token_b']['address']
            loan_amount = int(self.calculate_optimal_loan_amount(opportunity) * 10**18)
            dex_router1 = opportunity['exchange1']['router']
            dex_router2 = opportunity['exchange2']['router']
            min_profit = int(self.min_profit_threshold * 10**18)
            
            # Execute flashloan
            tx_hash = await self.contract_integration.execute_arbitrage(
                token_a, token_b, loan_amount, dex_router1, dex_router2, min_profit
            )
            
            # Create result
            result = {
                "transaction_hash": tx_hash,
                "opportunity": opportunity,
                "loan_amount": loan_amount,
                "explorer_url": self.contract_integration.get_explorer_url(tx_hash),
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Log and notify
            logger.info(f"Flashloan arbitrage executed: {tx_hash}")
            
            if hasattr(self, 'slack_bot') and self.slack_bot:
                await self.slack_bot.send_notification(
                    f"⚡ Flashloan arbitrage executed!\n"
                    f"Pair: {opportunity['token_a']['symbol']}/{opportunity['token_b']['symbol']}\n"
                    f"Profit: {opportunity['flashloan_profit']:.4f} ETH\n"
                    f"Tx: `{tx_hash}`\n"
                    f"Explorer: {result['explorer_url']}"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute flashloan arbitrage: {e}")
            raise
    
    async def monitor_and_execute(self):
        """Monitor for opportunities and execute flashloan arbitrage"""
        logger.info("Starting flashloan arbitrage monitoring...")
        
        while True:
            try:
                # Find opportunities
                opportunities = await self.find_arbitrage_opportunities_with_flashloan()
                
                if opportunities:
                    logger.info(f"Found {len(opportunities)} flashloan opportunities")
                    
                    # Sort by profit
                    opportunities.sort(key=lambda x: x['flashloan_profit'], reverse=True)
                    
                    # Execute the best opportunity
                    best_opp = opportunities[0]
                    
                    if best_opp['flashloan_profit'] > self.min_profit_threshold:
                        logger.info(f"Executing best opportunity: {best_opp}")
                        
                        result = await self.execute_flashloan_arbitrage(best_opp)
                        
                        # Log result
                        await self.log_arbitrage_result(result)
                        
                        # Wait before next execution
                        await asyncio.sleep(60)  # 1 minute cooldown
                    
                else:
                    logger.debug("No suitable flashloan opportunities found")
                
                # Wait before next scan
                await asyncio.sleep(30)  # 30 second scan interval
                
            except Exception as e:
                logger.error(f"Error in flashloan monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def log_arbitrage_result(self, result: Dict):
        """Log arbitrage execution results"""
        try:
            log_entry = {
                "timestamp": result['timestamp'],
                "transaction_hash": result['transaction_hash'],
                "explorer_url": result['explorer_url'],
                "opportunity": result['opportunity'],
                "loan_amount": result['loan_amount']
            }
            
            # Save to log file
            with open("flashloan_results.jsonl", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            
            logger.info(f"Logged flashloan result: {result['transaction_hash']}")
            
        except Exception as e:
            logger.error(f"Failed to log arbitrage result: {e}")
    
    async def get_contract_status(self) -> Dict:
        """Get current contract status"""
        if not self.contract_integration:
            return {"error": "Contract not initialized"}
        
        try:
            # Example token addresses (WETH and USDC on Polygon)
            weth_address = "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"
            usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
            
            weth_balance = await self.contract_integration.get_contract_balance(weth_address)
            usdc_balance = await self.contract_integration.get_contract_balance(usdc_address)
            
            return {
                "contract_address": self.contract_address,
                "network": self.contract_integration.network,
                "weth_balance": str(Web3.fromWei(weth_balance, 'ether')),
                "usdc_balance": str(Web3.fromWei(usdc_balance, 'mwei')),
                "account": self.contract_integration.account.address
            }
            
        except Exception as e:
            logger.error(f"Failed to get contract status: {e}")
            return {"error": str(e)}
    
    async def whitelist_tokens(self, tokens: List[str]):
        """Whitelist tokens for arbitrage"""
        if not self.contract_integration:
            raise Exception("Contract not initialized")
        
        try:
            # This would require contract owner to execute
            # For now, just log the request
            logger.info(f"Whitelisting tokens: {tokens}")
            
            # In production, implement actual whitelist functionality
            # This would require the contract owner's private key
            
        except Exception as e:
            logger.error(f"Failed to whitelist tokens: {e}")
            raise
    
    async def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        try:
            # Read flashloan results
            results = []
            try:
                with open("flashloan_results.jsonl", "r") as f:
                    for line in f:
                        results.append(json.loads(line))
            except FileNotFoundError:
                results = []
            
            # Calculate metrics
            total_executions = len(results)
            total_profit = sum(Decimal(str(r['opportunity'].get('flashloan_profit', 0))) 
                             for r in results)
            
            return {
                "total_executions": total_executions,
                "total_profit": str(total_profit),
                "average_profit": str(total_profit / max(total_executions, 1)),
                "last_execution": results[-1]['timestamp'] if results else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}

# Example usage
async def main():
    """Example usage of flashloan bot"""
    
    # Initialize bot
    bot = FlashLoanBot()
    await bot.initialize()
    
    # Initialize flashloan
    await bot.initialize_flashloan(
        network="polygon",
        contract_address="0x...",  # Your deployed contract address
        private_key=os.getenv("POLYGON_PRIVATE_KEY")
    )
    
    # Start monitoring
    await bot.monitor_and_execute()

if __name__ == "__main__":
    import os
    asyncio.run(main())